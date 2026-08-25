"""Add learning progress and approved email campaigns."""

import sqlalchemy as sa
from alembic import op

revision = "0005_growth_modules"
down_revision = "0004_website_chatbot"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learning_progress",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("lesson_key", sa.String(80), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "lesson_key", name="uq_learning_user_lesson"),
    )
    op.create_table(
        "email_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("reply_to", sa.String(255)),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "email_recipients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160)),
        sa.Column("company_name", sa.String(255)),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text()),
        sa.Column("sent_at", sa.DateTime()),
        sa.UniqueConstraint("campaign_id", "email", name="uq_campaign_email"),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("learning_progress", "email_campaigns"):
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'''CREATE POLICY "{table}_own" ON public."{table}" FOR ALL TO authenticated
                USING (user_id::text = auth.uid()::text) WITH CHECK (user_id::text = auth.uid()::text)''')
        op.execute('ALTER TABLE public."email_recipients" ENABLE ROW LEVEL SECURITY')
        op.execute('''CREATE POLICY "email_recipients_own" ON public."email_recipients" FOR SELECT TO authenticated USING (
            EXISTS (SELECT 1 FROM public.email_campaigns c WHERE c.id = email_recipients.campaign_id
            AND c.user_id::text = auth.uid()::text))''')


def downgrade():
    op.drop_table("email_recipients")
    op.drop_table("email_campaigns")
    op.drop_table("learning_progress")
