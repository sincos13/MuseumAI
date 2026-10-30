"""Museum knowledge upload, editing and indexing."""

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.api.deps import CurrentAdmin, RateLimitDep, SessionDep, UnifiedIndexingServiceDep
from app.api.documents import (
    KnowledgeMetadata,
    process_document_background,
    store_document_upload,
    validate_knowledge_content,
    validate_knowledge_scope,
)
from app.application.document_service import (
    SANITIZED_ERROR_MESSAGE,
    count_all_documents,
    delete_document_by_id,
    get_all_documents,
    get_ingestion_job_by_document,
    update_document_status,
)
from app.infra.postgres.adapters.document_repository import PostgresDocumentRepository
from app.infra.postgres.models import Document

router = APIRouter(prefix="/admin/documents", tags=["admin-documents"])
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class AdminDocumentResponse(KnowledgeMetadata):
    id: str
    filename: str
    status: str
    error: str | None = None
    created_at: str
    revision: int
    indexed_revision: int
    chunk_count: int


class AdminDocumentDetailResponse(AdminDocumentResponse):
    content_text: str | None


class AdminDocumentListResponse(BaseModel):
    documents: list[AdminDocumentResponse]
    total: int
    limit: int
    offset: int


class AdminDocumentPatch(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    source_label: str | None = Field(default=None, max_length=500)
    source_url: str | None = Field(default=None, max_length=2000)
    hall_slug: str | None = Field(default=None, max_length=100)
    content_text: str | None = Field(default=None, max_length=50 * 1024 * 1024)
    model_config = {"extra": "forbid"}


class AdminIngestionJobResponse(BaseModel):
    id: str
    document_id: str
    status: str
    chunk_count: int
    error: str | None
    created_at: str
    updated_at: str


class AdminDocumentDeleteResponse(BaseModel):
    status: str
    document_id: str


async def _locked_document(session, doc_id: str) -> Document:
    document = (
        await session.execute(
            select(Document).where(Document.id == doc_id).with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


async def _document_response(session, document: Document, *, detail: bool = False):
    job = await get_ingestion_job_by_document(PostgresDocumentRepository(session), document.id)
    values = dict(
        id=document.id, filename=document.filename, status=document.status,
        error=SANITIZED_ERROR_MESSAGE if document.error else None,
        created_at=document.created_at.isoformat(), title=document.title,
        source_label=document.source_label, source_url=document.source_url,
        hall_slug=document.hall_slug,
        revision=document.revision, indexed_revision=document.indexed_revision,
        chunk_count=job.chunk_count if job else 0,
    )
    if detail:
        return AdminDocumentDetailResponse(**values, content_text=document.content_text)
    return AdminDocumentResponse(**values)


@router.get("", response_model=AdminDocumentListResponse, summary="List knowledge documents (admin)")
async def list_documents_admin(
    session: SessionDep, current_admin: CurrentAdmin,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = Query(0, ge=0),
) -> AdminDocumentListResponse:
    doc_repo = PostgresDocumentRepository(session)
    documents = await get_all_documents(doc_repo, limit=limit, offset=offset)
    return AdminDocumentListResponse(
        documents=[await _document_response(session, document) for document in documents],
        total=await count_all_documents(doc_repo), limit=limit, offset=offset,
    )


@router.get("/{doc_id}", response_model=AdminDocumentDetailResponse, summary="Preview knowledge original (admin)")
async def get_document_admin(
    session: SessionDep, doc_id: str, current_admin: CurrentAdmin,
) -> AdminDocumentDetailResponse:
    document = await PostgresDocumentRepository(session).get_by_id(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return await _document_response(session, document, detail=True)


@router.get("/{doc_id}/status", response_model=AdminIngestionJobResponse, summary="Get indexing status (admin)")
async def get_document_status_admin(
    session: SessionDep, doc_id: str, current_admin: CurrentAdmin,
) -> AdminIngestionJobResponse:
    doc_repo = PostgresDocumentRepository(session)
    if await doc_repo.get_by_id(doc_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    job = await get_ingestion_job_by_document(doc_repo, doc_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return AdminIngestionJobResponse(
        id=job.id, document_id=job.document_id, status=job.status, chunk_count=job.chunk_count,
        error=SANITIZED_ERROR_MESSAGE if job.error else None,
        created_at=job.created_at.isoformat(), updated_at=job.updated_at.isoformat(),
    )


@router.post("/upload", response_model=AdminDocumentResponse, summary="Upload museum knowledge (admin)")
async def upload_document_admin(
    session: SessionDep, background_tasks: BackgroundTasks, current_admin: CurrentAdmin,
    _: RateLimitDep, unified_indexing_service: UnifiedIndexingServiceDep,
    file: UploadFile = File(...),  # noqa: B008
    title: str = Form("", max_length=255),  # noqa: B008
    source_label: str = Form("", max_length=500),  # noqa: B008
    source_url: str = Form("", max_length=2000),  # noqa: B008
    hall_slug: str | None = Form(None, max_length=100),  # noqa: B008
) -> AdminDocumentResponse:
    try:
        metadata = KnowledgeMetadata(title=title, source_label=source_label, source_url=source_url, hall_slug=hall_slug)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid knowledge metadata or source URL") from exc
    document = await store_document_upload(session, current_admin, file, metadata)
    background_tasks.add_task(
        process_document_background, document.id, None, document.filename, unified_indexing_service, document.revision,
    )
    return await _document_response(session, document)


@router.patch("/{doc_id}", response_model=AdminDocumentDetailResponse, summary="Edit museum knowledge (admin)")
async def patch_document_admin(
    session: SessionDep, doc_id: str, payload: AdminDocumentPatch,
    background_tasks: BackgroundTasks, current_admin: CurrentAdmin,
    unified_indexing_service: UnifiedIndexingServiceDep,
) -> AdminDocumentDetailResponse:
    document = await _locked_document(session, doc_id)
    if document.status in {"pending", "processing"}:
        raise HTTPException(status_code=409, detail="Document is being indexed; wait before editing")
    changes = payload.model_dump(exclude_unset=True)
    metadata_values = {key: getattr(document, key) for key in KnowledgeMetadata.model_fields}
    metadata_values.update({key: value for key, value in changes.items() if key != "content_text"})
    try:
        metadata = KnowledgeMetadata(**metadata_values)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid knowledge metadata or source URL") from exc
    # Existing references to a deactivated hall may be edited to museum-wide.
    await validate_knowledge_scope(session, metadata.hall_slug)
    content_changed = "content_text" in changes and changes["content_text"] != document.content_text
    if "content_text" in changes:
        if changes["content_text"] is None:
            raise HTTPException(status_code=422, detail="Knowledge content cannot be null")
        validate_knowledge_content(changes["content_text"])
    for key, value in metadata.model_dump().items():
        setattr(document, key, value)
    if content_changed:
        document.content_text = changes["content_text"]
        document.revision += 1
        document.indexed_revision = 0
        await update_document_status(PostgresDocumentRepository(session), doc_id, "pending", None, 0)
    await session.commit()
    if content_changed:
        background_tasks.add_task(
            process_document_background, doc_id, None, document.filename, unified_indexing_service, document.revision,
        )
    return await _document_response(session, document, detail=True)


@router.post("/{doc_id}/reindex", response_model=AdminDocumentResponse, summary="Rebuild knowledge index (admin)")
async def reindex_document_admin(
    session: SessionDep, doc_id: str, background_tasks: BackgroundTasks,
    current_admin: CurrentAdmin, unified_indexing_service: UnifiedIndexingServiceDep,
) -> AdminDocumentResponse:
    document = await _locked_document(session, doc_id)
    if document.status == "processing":
        raise HTTPException(status_code=409, detail="Document is already being indexed")
    if document.content_text is None:
        raise HTTPException(status_code=409, detail="Legacy document has no retained original; re-upload it first")
    validate_knowledge_content(document.content_text)
    document.revision += 1
    document.indexed_revision = 0
    await update_document_status(PostgresDocumentRepository(session), doc_id, "pending", None, 0)
    await session.commit()
    background_tasks.add_task(
        process_document_background, doc_id, None, document.filename, unified_indexing_service, document.revision,
    )
    return await _document_response(session, document)


@router.delete("/{doc_id}", response_model=AdminDocumentDeleteResponse, summary="Delete knowledge (admin)")
async def delete_document_admin(
    session: SessionDep, doc_id: str, current_admin: CurrentAdmin,
    unified_indexing_service: UnifiedIndexingServiceDep,
) -> AdminDocumentDeleteResponse:
    if not await delete_document_by_id(PostgresDocumentRepository(session), doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        await unified_indexing_service.delete_source(doc_id, source_type="document")
    except Exception:
        # Keep the original API behavior when search cleanup is unavailable.
        pass
    return AdminDocumentDeleteResponse(status="deleted", document_id=doc_id)
