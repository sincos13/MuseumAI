"""Persist the identity-agnostic final visitor report."""
import sqlalchemy as sa
from alembic import op

revision = "20261029_final_tour_report"
down_revision = "20261028_personal_tour_report"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tour_reports", sa.Column("final_report", sa.JSON(), nullable=True))
    op.add_column("tour_reports", sa.Column("final_report_hash", sa.String(64), nullable=True))


def downgrade():
    op.drop_column("tour_reports", "final_report_hash")
    op.drop_column("tour_reports", "final_report")
