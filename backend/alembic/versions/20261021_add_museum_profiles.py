"""Add deployment-wide museum configuration with optimistic revisions.

Revision ID: 20261021_museum_profiles
Revises: 20260809_trusted_hall_chat_history
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_museum_profiles"
down_revision: str | None = "20260809_trusted_hall_chat_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Development startup also runs metadata.create_all. Never overwrite saved data.
    if not op.get_context().as_sql and sa.inspect(op.get_bind()).has_table("museum_profiles"):
        return
    op.create_table(
        "museum_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_museum_profiles_singleton"),
        sa.CheckConstraint("revision >= 1", name="ck_museum_profiles_revision"),
        sa.CheckConstraint("schema_version = 1", name="ck_museum_profiles_schema_version"),
    )


def downgrade() -> None:
    op.drop_table("museum_profiles")
