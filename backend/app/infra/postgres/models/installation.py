"""Identity and resumable bootstrap state for an independently deployed museum."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.postgres.models.base import Base


class MuseumInstallation(Base):
    __tablename__ = "museum_installation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    museum_id: Mapped[str] = mapped_column(String(64), nullable=False)
    package_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    search_index: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
