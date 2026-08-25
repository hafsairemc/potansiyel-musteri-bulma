"""Store and validate the source schema of uploaded fair files."""

import sqlalchemy as sa
from alembic import op

revision = "0016_fair_source_columns"
down_revision = "0015_email_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("fair_analyses", sa.Column("source_columns", sa.JSON(), nullable=False, server_default="[]"))


def downgrade():
    op.drop_column("fair_analyses", "source_columns")
