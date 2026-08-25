"""Store email evidence without claiming unverified addresses are verified."""

import sqlalchemy as sa
from alembic import op

revision = "0015_email_evidence"
down_revision = "0014_export_filters"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("crawler_companies", sa.Column("email_status", sa.String(length=30), nullable=True))
    op.add_column("crawler_companies", sa.Column("email_source_url", sa.Text(), nullable=True))
    op.execute("UPDATE crawler_companies SET email_status = 'public_source' WHERE email IS NOT NULL AND email <> ''")


def downgrade():
    op.drop_column("crawler_companies", "email_source_url")
    op.drop_column("crawler_companies", "email_status")
