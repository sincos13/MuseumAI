"""Track independent installations without changing existing museums."""

import sqlalchemy as sa
from alembic import op

revision = "20261024_museum_installation"
down_revision = "20261024_knowledge_publication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "museum_installation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("museum_id", sa.String(64), nullable=False),
        sa.Column("package_digest", sa.String(64), nullable=False),
        sa.Column("search_index", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("museum_installation")
