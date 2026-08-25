"""Add optional email reply tracking."""

import sqlalchemy as sa
from alembic import op

revision = "0010_email_replies"
down_revision = "0009_email_tracking"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("email_recipients")}
    additions = (
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("reply_subject", sa.String(500), nullable=True),
        sa.Column("reply_from", sa.String(255), nullable=True),
    )
    for column in additions:
        if column.name not in columns:
            op.add_column("email_recipients", column)
    constraints = {item["name"] for item in sa.inspect(bind).get_unique_constraints("email_recipients")}
    if "uq_email_recipient_message_id" in constraints:
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("email_recipients") as batch:
            batch.create_unique_constraint("uq_email_recipient_message_id", ["message_id"])
    else:
        op.create_unique_constraint("uq_email_recipient_message_id", "email_recipients", ["message_id"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("email_recipients") as batch:
            batch.drop_constraint("uq_email_recipient_message_id", type_="unique")
            batch.drop_column("reply_from")
            batch.drop_column("reply_subject")
            batch.drop_column("replied_at")
            batch.drop_column("message_id")
    else:
        op.drop_constraint("uq_email_recipient_message_id", "email_recipients", type_="unique")
        op.drop_column("email_recipients", "reply_from")
        op.drop_column("email_recipients", "reply_subject")
        op.drop_column("email_recipients", "replied_at")
        op.drop_column("email_recipients", "message_id")
