"""Transactional storage for one museum; callers own commit/rollback."""

from datetime import UTC, datetime

from sqlalchemy import Text, cast, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.museum_profile import MuseumConfiguration, MuseumConfigurationUpdate, default_museum_profile
from app.infra.postgres.models.museum_profile import MuseumProfileModel
from app.infra.postgres.models.tour import TourSessionModel


class MuseumConfigurationConflict(Exception):
    """Another administrator has saved since the caller loaded its revision."""


def _missing_session_configuration():
    column = TourSessionModel.museum_configuration
    # Older ORM versions serialized Python None as JSON null. PostgreSQL JSON
    # has no equality operator, so use a portable text cast for that legacy case.
    return or_(column.is_(None), cast(column, Text) == "null")


async def get_session_museum_configuration(session: AsyncSession, tour_session_id: str) -> MuseumConfiguration:
    """Resolve a server-owned snapshot; legacy sessions freeze on first use."""
    result = await session.execute(
        select(TourSessionModel.museum_configuration).where(TourSessionModel.id == tour_session_id)
    )
    row = result.one_or_none()
    if row is None:
        from app.domain.exceptions import TourSessionNotFound

        raise TourSessionNotFound(tour_session_id)
    if row[0] is not None:
        return MuseumConfiguration.model_validate(row[0])
    config = await get_museum_configuration(session)
    await session.execute(
        update(TourSessionModel)
        .where(TourSessionModel.id == tour_session_id, _missing_session_configuration())
        .values(museum_configuration=config.model_dump(mode="json"))
        .execution_options(synchronize_session=False)
    )
    # Re-read a concurrent first writer's chosen snapshot rather than returning
    # a different configuration for the same tour.
    snapshot = (
        await session.execute(
            select(TourSessionModel.museum_configuration).where(TourSessionModel.id == tour_session_id)
        )
    ).scalar_one()
    return MuseumConfiguration.model_validate(snapshot)


async def get_museum_configuration(session: AsyncSession) -> MuseumConfiguration:
    # Column selection avoids serving stale ORM identity-map data in a reused session.
    result = await session.execute(
        select(MuseumProfileModel.schema_version, MuseumProfileModel.revision, MuseumProfileModel.profile).where(
            MuseumProfileModel.id == 1
        )
    )
    row = result.one_or_none()
    if row is None:
        return MuseumConfiguration(revision=0, museum=default_museum_profile())
    return MuseumConfiguration(schema_version=row.schema_version, revision=row.revision, museum=row.profile)


async def save_museum_configuration(
    session: AsyncSession,
    update_request: MuseumConfigurationUpdate,
) -> MuseumConfiguration:
    previous = await get_museum_configuration(session)
    if previous.revision != update_request.expected_revision:
        raise MuseumConfigurationConflict("Configuration changed; reload before saving")
    next_profile = update_request.museum.model_copy(deep=True)
    if "business" not in update_request.museum.model_fields_set:
        # Old A-only clients and profile exports cannot reset a saved C configuration.
        next_profile.business = previous.museum.business.model_copy(deep=True)
    next_revision = update_request.expected_revision + 1
    values = {
        "schema_version": update_request.schema_version,
        "revision": next_revision,
        "profile": next_profile.model_dump(mode="json"),
        "updated_at": datetime.now(UTC),
    }
    if update_request.expected_revision == 0:
        # ON CONFLICT handles simultaneous first saves without aborting the caller's
        # transaction. Unlike nested SQLite savepoints it also preserves rollback.
        dialect = session.get_bind().dialect.name
        insert = sqlite_insert if dialect == "sqlite" else postgres_insert
        result = await session.execute(
            insert(MuseumProfileModel).values(id=1, **values).on_conflict_do_nothing(index_elements=["id"])
        )
        if result.rowcount != 1:
            raise MuseumConfigurationConflict("Configuration changed; reload before saving")
    else:
        result = await session.execute(
            update(MuseumProfileModel)
            .where(MuseumProfileModel.id == 1, MuseumProfileModel.revision == update_request.expected_revision)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise MuseumConfigurationConflict("Configuration changed; reload before saving")
    # Freeze legacy sessions to the prior complete configuration before the
    # profile transaction commits. Existing snapshots are immutable.
    await session.execute(
        update(TourSessionModel)
        .where(_missing_session_configuration())
        .values(museum_configuration=previous.model_dump(mode="json"))
        .execution_options(synchronize_session=False)
    )
    return MuseumConfiguration(revision=next_revision, museum=next_profile)
