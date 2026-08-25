"""Add transparent fair analysis row metrics."""

import sqlalchemy as sa
from alembic import op

revision = "0017_fair_analysis_metrics"
down_revision = "0016_fair_source_columns"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("fair_analyses", sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("fair_analyses", sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("fair_analyses", sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("fair_analyses", "duplicate_rows")
    op.drop_column("fair_analyses", "processed_rows")
    op.drop_column("fair_analyses", "total_rows")
