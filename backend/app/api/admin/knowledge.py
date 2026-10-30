"""Preview ordinary RAG retrieval without publication or revision gates."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.deps import CurrentAdminUser, RagAgentDep, SessionDep
from app.application.tour_chat_service import _filter_trusted_rag_documents
from app.infra.postgres.models import Document, Hall

router = APIRouter(prefix="/admin/knowledge", tags=["admin-knowledge"])


class KnowledgePreviewRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    hall_slug: str | None = Field(default=None, max_length=100)

    @field_validator("query")
    @classmethod
    def nonempty_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请输入有效问题")
        return value.strip()


@router.post("/search-preview")
async def search_preview(
    body: KnowledgePreviewRequest,
    _admin: CurrentAdminUser,
    session: SessionDep,
    rag_agent: RagAgentDep,
) -> dict:
    if body.hall_slug is not None:
        hall = await session.get(Hall, body.hall_slug)
        if hall is None or not hall.is_active:
            raise HTTPException(status_code=404, detail="展厅不存在或已停用")
    result = await rag_agent.run(body.query, skip_generate=True)
    documents = (
        result.get("filtered_documents")
        or result.get("reranked_documents")
        or result.get("documents", [])
    )
    if body.hall_slug is not None:
        documents = await _filter_trusted_rag_documents(session, documents, body.hall_slug)
    sources = []
    for document in documents:
        metadata = document.metadata
        record = None
        if metadata.get("source_type") == "document" and metadata.get("source_id"):
            record = await session.get(Document, str(metadata["source_id"]))
        sources.append({
            "source_id": metadata.get("source_id"),
            "source_type": metadata.get("source_type"),
            "title": (record.title or record.filename) if record else metadata.get("source") or "检索资料",
            "source_label": record.source_label if record else "",
            "source_url": record.source_url if record else "",
            "hall_slug": record.hall_slug if record else metadata.get("hall"),
            "content": document.page_content[:800],
        })
    return {"query": body.query, "sources": sources, "total": len(sources)}
