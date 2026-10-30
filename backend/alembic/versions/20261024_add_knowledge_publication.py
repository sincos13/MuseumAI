"""Retain museum knowledge originals and require an explicit publication review."""

import sqlalchemy as sa
from alembic import op

revision = "20261024_knowledge_publication"
down_revision = "20261022_business_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing indexed files have no retained original or revision marker. Keep
    # them as drafts so operators must re-upload and review their own knowledge.
    op.add_column("documents", sa.Column("title", sa.String(255), server_default="", nullable=False))
    op.add_column("documents", sa.Column("source_label", sa.String(500), server_default="", nullable=False))
    op.add_column("documents", sa.Column("source_url", sa.String(2000), server_default="", nullable=False))
    op.add_column("documents", sa.Column("hall_slug", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("published", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("documents", sa.Column("content_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("revision", sa.Integer(), server_default="1", nullable=False))
    op.add_column("documents", sa.Column("indexed_revision", sa.Integer(), server_default="0", nullable=False))
    op.create_index("ix_documents_hall_slug", "documents", ["hall_slug"])
    op.create_index("ix_documents_published", "documents", ["published"])


def downgrade() -> None:
    op.drop_index("ix_documents_published", table_name="documents")
    op.drop_index("ix_documents_hall_slug", table_name="documents")
    for name in ("indexed_revision", "revision", "content_text", "published", "hall_slug",
                 "source_url", "source_label", "title"):
        op.drop_column("documents", name)
