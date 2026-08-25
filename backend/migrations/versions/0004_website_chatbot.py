"""Add embeddable website chatbot and lead tables."""

import sqlalchemy as sa
from alembic import op


revision = "0004_website_chatbot"
down_revision = "0003_intelligence_modules"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "website_bots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("public_key", sa.String(48), nullable=False, unique=True),
        sa.Column("welcome_message", sa.Text(), nullable=False),
        sa.Column("knowledge", sa.Text()),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("allowed_domains", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "website_bot_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bot_id", sa.String(36), sa.ForeignKey("website_bots.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("session_id", sa.String(80), nullable=False, index=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("bot_id", "session_id", name="uq_website_bot_session"),
    )
    op.create_table(
        "website_bot_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("website_bot_conversations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "website_bot_leads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bot_id", sa.String(36), sa.ForeignKey("website_bots.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("session_id", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(120)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(80)),
        sa.Column("consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE public."website_bots" ENABLE ROW LEVEL SECURITY')
        op.execute('CREATE POLICY "website_bots_own" ON public."website_bots" FOR ALL TO authenticated USING (user_id::text = auth.uid()::text) WITH CHECK (user_id::text = auth.uid()::text)')
        for table, column, parent in (
            ("website_bot_conversations", "bot_id", "website_bots"),
            ("website_bot_leads", "bot_id", "website_bots"),
        ):
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'''CREATE POLICY "{table}_own" ON public."{table}" FOR SELECT TO authenticated USING (
                EXISTS (SELECT 1 FROM public."{parent}" b WHERE b.id = "{table}"."{column}" AND b.user_id::text = auth.uid()::text))''')
        op.execute('ALTER TABLE public."website_bot_messages" ENABLE ROW LEVEL SECURITY')
        op.execute('''CREATE POLICY "website_bot_messages_own" ON public."website_bot_messages" FOR SELECT TO authenticated USING (
            EXISTS (SELECT 1 FROM public.website_bot_conversations c JOIN public.website_bots b ON b.id = c.bot_id
            WHERE c.id = website_bot_messages.conversation_id AND b.user_id::text = auth.uid()::text))''')


def downgrade():
    op.drop_table("website_bot_leads")
    op.drop_table("website_bot_messages")
    op.drop_table("website_bot_conversations")
    op.drop_table("website_bots")
