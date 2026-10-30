"""Museum knowledge upload, indexing and safe public document reads."""

import os
import tempfile
from urllib.parse import urlsplit

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.api._shared_responses import DocumentDeleteResponse as DeleteResponse
from app.api.deps import CurrentAdmin, OptionalUser, RateLimitDep, SessionDep, UnifiedIndexingServiceDep
from app.application.content_source import ContentMetadata, ContentSource
from app.application.document_service import (
    SANITIZED_ERROR_MESSAGE,
    count_all_documents,
    create_document,
    delete_document_by_id,
    get_all_documents,
    get_ingestion_job_by_document,
    update_document_status,
)
from app.application.unified_indexing_service import UnifiedIndexingService
from app.infra.postgres.adapters.document_repository import PostgresDocumentRepository
from app.infra.postgres.database import get_session, get_session_maker
from app.infra.postgres.models import Document, Hall

router = APIRouter(prefix="/documents", tags=["documents"])
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_FILE_SIZE = 50 * 1024 * 1024
CHUNK_SIZE = 64 * 1024
ALLOWED_EXTENSIONS = frozenset({".txt", ".md", ".markdown"})
ALLOWED_CONTENT_TYPES = frozenset({"text/plain", "text/markdown", "text/x-markdown", "application/octet-stream"})


class KnowledgeMetadata(BaseModel):
    title: str = Field(default="", max_length=255)
    source_label: str = Field(default="", max_length=500)
    source_url: str = Field(default="", max_length=2000)
    hall_slug: str | None = Field(default=None, max_length=100)

    @field_validator("title", "source_label", "source_url", "hall_slug", mode="before")
    @classmethod
    def trim_metadata(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("hall_slug")
    @classmethod
    def empty_scope_is_museum_wide(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        if value:
            try:
                parsed = urlsplit(value)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                    raise ValueError("Source URL must be an http/https URL without credentials")
            except ValueError as exc:
                raise ValueError("Source URL must be an http/https URL without credentials") from exc
        return value


class PublicDocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    created_at: str


class PublicDocumentListResponse(BaseModel):
    documents: list[PublicDocumentResponse]
    total: int
    limit: int
    offset: int


class PublicIngestionJobResponse(BaseModel):
    id: str
    document_id: str
    status: str
    chunk_count: int
    created_at: str
    updated_at: str


class DocumentResponse(PublicDocumentResponse):
    error: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class IngestionJobResponse(PublicIngestionJobResponse):
    error: str | None


def validate_upload_metadata(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if len(file.filename) > 255:
        raise HTTPException(status_code=400, detail="Filename is too long")
    if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=415, detail=f"File extension not allowed. Accepted: {sorted(ALLOWED_EXTENSIONS)}",
        )
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Content-type not allowed")


def validate_knowledge_content(content: str) -> str:
    if not content.strip("\ufeff \t\r\n"):
        raise HTTPException(status_code=400, detail="Knowledge content must not be empty")
    if "\x00" in content:
        raise HTTPException(status_code=415, detail="File content appears binary (null bytes detected)")
    try:
        encoded_size = len(content.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise HTTPException(status_code=415, detail="Knowledge content must be valid UTF-8 text") from exc
    if encoded_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    return content


def validate_upload_content(temp_path: str) -> str:
    """Validate the whole file, including bytes beyond the original 8 KiB sniff."""
    try:
        with open(temp_path, encoding="utf-8-sig") as source:
            content = source.read()
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="File content is not valid UTF-8 text") from exc
    return validate_knowledge_content(content)


async def validate_knowledge_scope(session, hall_slug: str | None) -> None:
    if hall_slug:
        hall = await session.get(Hall, hall_slug)
        if hall is None or not hall.is_active:
            raise HTTPException(status_code=422, detail="Knowledge scope must be an active hall")


async def stream_to_temp_file(file: UploadFile, max_size: int) -> tuple[str, int]:
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tmp", prefix="museai_upload_")
    os.close(tmp_fd)
    total_size = 0
    try:
        async with aiofiles.open(tmp_path, "wb") as destination:
            while chunk := await file.read(CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > max_size:
                    raise HTTPException(status_code=413, detail="File too large (max 50MB)")
                await destination.write(chunk)
    except BaseException:
        os.unlink(tmp_path)
        raise
    return tmp_path, total_size


async def store_document_upload(session, current_admin, file: UploadFile, metadata: KnowledgeMetadata) -> Document:
    """Retain the validated original in PostgreSQL; indexing starts automatically."""
    validate_upload_metadata(file)
    await validate_knowledge_scope(session, metadata.hall_slug)
    tmp_path, _ = await stream_to_temp_file(file, MAX_FILE_SIZE)
    try:
        content = validate_upload_content(tmp_path)
        document = await create_document(
            PostgresDocumentRepository(session), file.filename, current_admin["id"],
            **metadata.model_dump(), content_text=content,
        )
        await session.commit()
        return document
    finally:
        os.unlink(tmp_path)


async def process_document_background(
    document_id: str,
    temp_file_path: str | None,
    filename: str,
    unified_indexing_service: UnifiedIndexingService,
    expected_revision: int = 1,
):
    """Index retained text; revision checks only prevent stale background jobs from overwriting newer edits."""
    try:
        async with get_session(get_session_maker()) as session:
            doc_repo = PostgresDocumentRepository(session)
            try:
                stmt = select(Document).where(Document.id == document_id).with_for_update()
                document = (await session.execute(stmt)).scalar_one_or_none()
                if document is None or document.revision != expected_revision or document.status != "pending":
                    return
                content = validate_knowledge_content(document.content_text or "")
                await update_document_status(doc_repo, document_id, "processing", None, 0)
                await session.commit()

                source = ContentSource(
                    source_id=document_id, source_type="document", content=content,
                    metadata=ContentMetadata(filename=filename, extra={
                        "knowledge_revision": expected_revision, "title": document.title,
                        "source_label": document.source_label, "hall": document.hall_slug,
                    }),
                )
                # An older longer revision must not leave trailing chunks.
                await unified_indexing_service.delete_source(document_id, source_type="document")
                chunk_count = await unified_indexing_service.index_source(source)
                if chunk_count <= 0:
                    raise ValueError("Indexing produced no content")
                await unified_indexing_service.refresh_index()

                document = (
                    await session.execute(stmt.execution_options(populate_existing=True))
                ).scalar_one_or_none()
                if document is None or document.revision != expected_revision or document.status != "processing":
                    return
                document.indexed_revision = expected_revision
                await update_document_status(doc_repo, document_id, "completed", None, chunk_count)
                await session.commit()
                logger.info("Document {} revision {} indexed: {} chunks", document_id, expected_revision, chunk_count)
            except Exception:
                logger.exception("Failed to process document {}", document_id)
                await session.rollback()
                document = (
                    await session.execute(
                        select(Document).where(Document.id == document_id).with_for_update()
                        .execution_options(populate_existing=True)
                    )
                ).scalar_one_or_none()
                if document is not None and document.revision == expected_revision:
                    document.indexed_revision = 0
                    await update_document_status(doc_repo, document_id, "failed", SANITIZED_ERROR_MESSAGE, 0)
                    await session.commit()
    finally:
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
            except OSError:
                logger.warning("Failed to delete temporary upload")


@router.post("/upload", response_model=DocumentResponse, summary="Upload document (admin only)")
async def upload_document(
    session: SessionDep, background_tasks: BackgroundTasks, current_admin: CurrentAdmin,
    _: RateLimitDep, unified_indexing_service: UnifiedIndexingServiceDep,
    file: UploadFile = File(...),  # noqa: B008
    title: str = Form("", max_length=255),  # noqa: B008
    source_label: str = Form("", max_length=500),  # noqa: B008
    source_url: str = Form("", max_length=2000),  # noqa: B008
    hall_slug: str | None = Form(None, max_length=100),  # noqa: B008
) -> DocumentResponse:
    try:
        metadata = KnowledgeMetadata(title=title, source_label=source_label, source_url=source_url, hall_slug=hall_slug)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid knowledge metadata or source URL") from exc
    document = await store_document_upload(session, current_admin, file, metadata)
    background_tasks.add_task(
        process_document_background, document.id, None, file.filename, unified_indexing_service, document.revision,
    )
    return DocumentResponse(
        id=document.id, filename=document.filename, status=document.status,
        error=SANITIZED_ERROR_MESSAGE if document.error else None, created_at=document.created_at.isoformat(),
    )


@router.get("", response_model=PublicDocumentListResponse, summary="List documents")
async def list_documents(
    session: SessionDep, _: OptionalUser,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = Query(0, ge=0),
) -> PublicDocumentListResponse:
    doc_repo = PostgresDocumentRepository(session)
    documents = await get_all_documents(doc_repo, limit=limit, offset=offset)
    return PublicDocumentListResponse(
        documents=[PublicDocumentResponse(
            id=doc.id, filename=doc.filename, status=doc.status, created_at=doc.created_at.isoformat(),
        ) for doc in documents],
        total=await count_all_documents(doc_repo), limit=limit, offset=offset,
    )


@router.get("/{doc_id}", response_model=PublicDocumentResponse, summary="Get document detail")
async def get_document(session: SessionDep, doc_id: str, _: OptionalUser) -> PublicDocumentResponse:
    document = await PostgresDocumentRepository(session).get_by_id(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return PublicDocumentResponse(
        id=document.id, filename=document.filename, status=document.status, created_at=document.created_at.isoformat(),
    )


@router.get("/{doc_id}/status", response_model=PublicIngestionJobResponse, summary="Get document ingestion status")
async def get_document_status(session: SessionDep, doc_id: str, _: OptionalUser) -> PublicIngestionJobResponse:
    doc_repo = PostgresDocumentRepository(session)
    document = await doc_repo.get_by_id(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    job = await get_ingestion_job_by_document(doc_repo, doc_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return PublicIngestionJobResponse(
        id=job.id, document_id=job.document_id, status=job.status, chunk_count=job.chunk_count,
        created_at=job.created_at.isoformat(), updated_at=job.updated_at.isoformat(),
    )


@router.delete("/{doc_id}", response_model=DeleteResponse, summary="Delete document (admin only)")
async def delete_document_endpoint(
    session: SessionDep, doc_id: str, current_admin: CurrentAdmin,
    unified_indexing_service: UnifiedIndexingServiceDep,
) -> DeleteResponse:
    if not await delete_document_by_id(PostgresDocumentRepository(session), doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        await unified_indexing_service.delete_source(doc_id, source_type="document")
    except Exception:
        logger.exception("Failed to remove orphaned document chunks {}", doc_id)
    return DeleteResponse(status="deleted", document_id=doc_id)
