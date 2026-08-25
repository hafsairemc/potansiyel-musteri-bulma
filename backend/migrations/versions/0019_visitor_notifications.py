"""Add user-owned visitor notifications."""

import sqlalchemy as sa
from alembic import op

revision = "0019_visitor_notifications"
down_revision = "0018_legacy_schema_repair"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "visitor_notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "visitor_id",
            sa.String(36),
            sa.ForeignKey("visitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("read_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "visitor_id",
            "user_id",
            name="uq_visitor_notification_owner",
        ),
    )
    op.create_index(
        "ix_visitor_notifications_visitor_id",
        "visitor_notifications",
        ["visitor_id"],
    )
    op.create_index(
        "ix_visitor_notifications_user_id",
        "visitor_notifications",
        ["user_id"],
    )
    op.create_index(
        "ix_visitor_notifications_read_at",
        "visitor_notifications",
        ["read_at"],
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            'ALTER TABLE public."visitor_notifications" ENABLE ROW LEVEL SECURITY'
        )
        op.execute(
            'CREATE POLICY "visitor_notifications_own" '
            'ON public."visitor_notifications" FOR SELECT TO authenticated '
            "USING (user_id::text = auth.uid()::text)"
        )
        op.execute(
            'CREATE POLICY "visitor_notifications_update_own" '
            'ON public."visitor_notifications" FOR UPDATE TO authenticated '
            "USING (user_id::text = auth.uid()::text) "
            "WITH CHECK (user_id::text = auth.uid()::text)"
        )
        op.execute(
            "REVOKE INSERT, DELETE ON public.visitor_notifications "
            "FROM authenticated, anon"
        )


def downgrade():
    op.drop_table("visitor_notifications")
