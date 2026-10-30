"""Persist source-bound personalized visit keepsakes."""
import sqlalchemy as sa
from alembic import op

revision = "20261028_personal_tour_report"
down_revision = "20261024_museum_installation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tour_reports", sa.Column("personal_report", sa.JSON(), nullable=True))
    op.add_column("tour_reports", sa.Column("personal_report_hash", sa.String(64), nullable=True))


def downgrade():
    op.drop_column("tour_reports", "personal_report_hash")
    op.drop_column("tour_reports", "personal_report")
