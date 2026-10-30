"""Database catalog access shared by management and public API boundaries."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.postgres.models import Hall


async def load_hall_catalog(session: AsyncSession, *, active_only: bool = False) -> list[Hall]:
    query = select(Hall).order_by(Hall.display_order, Hall.slug)
    if active_only:
        query = query.where(Hall.is_active.is_(True))
    return list((await session.execute(query)).scalars().all())


async def lock_hall_catalog(session: AsyncSession) -> None:
    # Names and aliases share one namespace, including rows not yet inserted.
    # Serialize catalog writers on PostgreSQL so two concurrent creates cannot
    # both pass the cross-column collision check. SQLite serializes writes itself.
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(682417235)"))
