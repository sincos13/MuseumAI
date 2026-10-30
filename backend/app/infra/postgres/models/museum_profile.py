from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.postgres.models.base import Base


class MuseumProfileModel(Base):
    """One configuration per deployment; id=1 is enforced by the database."""

    __tablename__ = "museum_profiles"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_museum_profiles_singleton"),
        CheckConstraint("revision >= 1", name="ck_museum_profiles_revision"),
        CheckConstraint("schema_version = 1", name="ck_museum_profiles_schema_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
