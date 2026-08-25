"""Store search filters used for Excel exports."""

import sqlalchemy as sa
from alembic import op

revision = "0014_export_filters"
down_revision = "0013_chatbot_lead_consent"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("search_exports", sa.Column("filters", sa.JSON(), nullable=False, server_default="{}"))


def downgrade():
    op.drop_column("search_exports", "filters")
