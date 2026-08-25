"""Add demand publication and email opt-out fields."""

import sqlalchemy as sa
from alembic import op

revision = "0006_demand_publication"
down_revision = "0005_growth_modules"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("email_recipients", sa.Column("unsubscribe_token", sa.String(64), nullable=True))
    op.add_column("email_recipients", sa.Column("unsubscribed_at", sa.DateTime()))
    op.create_index("uq_email_unsubscribe_token", "email_recipients", ["unsubscribe_token"], unique=True)
    op.create_table(
        "demand_posts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.String(100)),
        sa.Column("target_country", sa.String(100), nullable=False),
        sa.Column("deadline", sa.DateTime()),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "demand_post_targets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("demand_post_id", sa.String(36), sa.ForeignKey("demand_posts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("platform", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("publication_url", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("published_at", sa.DateTime()),
        sa.UniqueConstraint("demand_post_id", "platform", name="uq_demand_platform"),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE public."demand_posts" ENABLE ROW LEVEL SECURITY')
        op.execute('''CREATE POLICY "demand_posts_own" ON public."demand_posts" FOR ALL TO authenticated
            USING (user_id::text = auth.uid()::text) WITH CHECK (user_id::text = auth.uid()::text)''')
        op.execute('ALTER TABLE public."demand_post_targets" ENABLE ROW LEVEL SECURITY')
        op.execute('''CREATE POLICY "demand_post_targets_own" ON public."demand_post_targets" FOR SELECT TO authenticated USING (
            EXISTS (SELECT 1 FROM public.demand_posts p WHERE p.id = demand_post_targets.demand_post_id
            AND p.user_id::text = auth.uid()::text))''')


def downgrade():
    op.drop_table("demand_post_targets")
    op.drop_table("demand_posts")
    op.drop_index("uq_email_unsubscribe_token", table_name="email_recipients")
    op.drop_column("email_recipients", "unsubscribed_at")
    op.drop_column("email_recipients", "unsubscribe_token")
