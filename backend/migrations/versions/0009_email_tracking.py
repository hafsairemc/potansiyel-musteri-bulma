"""Add email campaign open tracking."""

import sqlalchemy as sa
from alembic import op

revision = "0009_email_tracking"
down_revision = "0008_trade_market_data"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("email_recipients")}
    additions = (
        sa.Column("tracking_token", sa.String(64), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("last_opened_at", sa.DateTime(), nullable=True),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
    )
    for column in additions:
        if column.name not in columns:
            op.add_column("email_recipients", column)
    constraints = {item["name"] for item in sa.inspect(bind).get_unique_constraints("email_recipients")}
    if "uq_email_recipient_tracking_token" in constraints:
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("email_recipients") as batch:
            batch.create_unique_constraint("uq_email_recipient_tracking_token", ["tracking_token"])
    else:
        op.create_unique_constraint("uq_email_recipient_tracking_token", "email_recipients", ["tracking_token"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("email_recipients") as batch:
            batch.drop_constraint("uq_email_recipient_tracking_token", type_="unique")
            batch.drop_column("open_count")
            batch.drop_column("last_opened_at")
            batch.drop_column("opened_at")
            batch.drop_column("tracking_token")
    else:
        op.drop_constraint("uq_email_recipient_tracking_token", "email_recipients", type_="unique")
        op.drop_column("email_recipients", "open_count")
        op.drop_column("email_recipients", "last_opened_at")
        op.drop_column("email_recipients", "opened_at")
        op.drop_column("email_recipients", "tracking_token")
