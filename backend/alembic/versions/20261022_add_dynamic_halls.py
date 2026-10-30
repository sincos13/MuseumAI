"""Add data-driven hall aliases and temporary exhibition metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_dynamic_halls"
down_revision: str | None = "20261021_museum_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    offline = op.get_context().as_sql
    columns = set() if offline else {column["name"] for column in sa.inspect(op.get_bind()).get_columns("halls")}
    if "aliases" not in columns:
        op.add_column("halls", sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"))
    if "is_temporary" not in columns:
        op.add_column("halls", sa.Column("is_temporary", sa.Boolean(), nullable=False, server_default=sa.false()))
        # One-time conversion of the legacy dataset. Runtime behavior uses this
        # column exclusively; arbitrary new slugs can also be temporary halls.
        op.execute(sa.text(
            "UPDATE halls SET is_temporary = true WHERE slug IN ('temporary-hall-1', 'temporary-hall-2')"
        ))


def downgrade() -> None:
    op.drop_column("halls", "is_temporary")
    op.drop_column("halls", "aliases")
