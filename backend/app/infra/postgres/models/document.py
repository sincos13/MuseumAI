from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.value_objects import DocumentId, JobId, UserId
from app.infra.postgres.models.base import Base

if TYPE_CHECKING:
    from app.infra.postgres.models.exhibit import Exhibit


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", server_default="", nullable=False)
    source_label: Mapped[str] = mapped_column(String(500), default="", server_default="", nullable=False)
    source_url: Mapped[str] = mapped_column(String(2000), default="", server_default="", nullable=False)
    hall_slug: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # Legacy storage only; publication is no longer part of retrieval or the API.
    published: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False, index=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    indexed_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def to_entity(self):
        from app.domain.entities import Document as DocumentEntity

        return DocumentEntity(
            id=DocumentId(self.id),
            user_id=UserId(self.user_id),
            filename=self.filename,
            status=self.status,
            created_at=self.created_at,
            error=self.error,
        )

    ingestion_jobs: Mapped[list[IngestionJob]] = relationship(back_populates="document", cascade="all, delete-orphan")
    exhibits: Mapped[list[Exhibit]] = relationship(back_populates="document")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def to_entity(self):
        from app.domain.entities import IngestionJob as IngestionJobEntity

        return IngestionJobEntity(
            id=JobId(self.id),
            document_id=DocumentId(self.document_id),
            status=self.status,
            chunk_count=self.chunk_count,
            created_at=self.created_at,
            error=self.error,
        )

    document: Mapped[Document] = relationship(back_populates="ingestion_jobs")
