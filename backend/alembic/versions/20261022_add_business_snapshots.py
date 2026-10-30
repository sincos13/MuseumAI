"""Keep each tour's questionnaire and report meanings stable across config edits."""

import sqlalchemy as sa
from alembic import op
from app.domain.museum_profile import MuseumConfiguration, default_museum_profile

revision = "20261022_business_snapshots"
down_revision = "20261022_dynamic_halls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = op.get_context().as_sql
    columns = set() if offline else {item["name"] for item in sa.inspect(op.get_bind()).get_columns("tour_sessions")}
    if "museum_configuration" not in columns:
        op.add_column("tour_sessions", sa.Column("museum_configuration", sa.JSON(none_as_null=True), nullable=True))
    if offline:
        # A data-dependent profile cannot be embedded in offline SQL. The online
        # migration, or first access/save, materializes the complete snapshot.
        return
    profiles = sa.table(
        "museum_profiles",
        sa.column("id"),
        sa.column("schema_version"),
        sa.column("revision"),
        sa.column("profile", sa.JSON()),
    )
    row = op.get_bind().execute(sa.select(profiles).where(profiles.c.id == 1)).mappings().first()
    configuration = (
        MuseumConfiguration(schema_version=row["schema_version"], revision=row["revision"], museum=row["profile"])
        if row is not None
        else MuseumConfiguration(revision=0, museum=default_museum_profile())
    )
    sessions = sa.table("tour_sessions", sa.column("museum_configuration", sa.JSON(none_as_null=True)))
    column = sessions.c.museum_configuration
    op.get_bind().execute(
        sessions.update()
        .where(
            sa.or_(column.is_(None), sa.cast(column, sa.Text) == "null"),
        )
        .values(museum_configuration=configuration.model_dump(mode="json"))
    )


def downgrade() -> None:
    op.drop_column("tour_sessions", "museum_configuration")
