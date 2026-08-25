"""Add provider delivery and bounce events."""

import sqlalchemy as sa
from alembic import op

revision = "0020_email_delivery_events"
down_revision = "0019_visitor_notifications"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "email_recipients",
        sa.Column("delivery_status", sa.String(30)),
    )
    op.add_column(
        "email_recipients",
        sa.Column("delivered_at", sa.DateTime()),
    )
    op.add_column(
        "email_recipients",
        sa.Column("bounced_at", sa.DateTime()),
    )
    op.add_column(
        "email_recipients",
        sa.Column("complained_at", sa.DateTime()),
    )
    op.add_column(
        "email_recipients",
        sa.Column("bounce_reason", sa.String(500)),
    )
    op.create_table(
        "email_delivery_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recipient_id",
            sa.String(36),
            sa.ForeignKey("email_recipients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "event_id",
            name="uq_email_delivery_event",
        ),
    )
    op.create_index(
        "ix_email_delivery_events_recipient_id",
        "email_delivery_events",
        ["recipient_id"],
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            'ALTER TABLE public."email_delivery_events" ENABLE ROW LEVEL SECURITY'
        )
        op.execute(
            "REVOKE ALL ON public.email_delivery_events FROM authenticated, anon"
        )


def downgrade():
    op.drop_table("email_delivery_events")
    op.drop_column("email_recipients", "bounce_reason")
    op.drop_column("email_recipients", "complained_at")
    op.drop_column("email_recipients", "bounced_at")
    op.drop_column("email_recipients", "delivered_at")
    op.drop_column("email_recipients", "delivery_status")
