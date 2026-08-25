"""Add user-owned UN Comtrade market snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0008_trade_market_data"
down_revision = "0007_admin_control"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "trade_market_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("target_country", sa.String(100), nullable=False),
        sa.Column("reporter_code", sa.String(20), nullable=False),
        sa.Column("reporter_name", sa.String(160)),
        sa.Column("hs_code", sa.String(10), nullable=False),
        sa.Column("commodity", sa.Text()),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("import_value_usd", sa.Float(), nullable=False),
        sa.Column("net_weight_kg", sa.Float()),
        sa.Column("quantity", sa.Float()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "product_id", "target_country", "period", "hs_code",
            name="uq_trade_market_snapshot",
        ),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE public."trade_market_snapshots" ENABLE ROW LEVEL SECURITY')
        op.execute('''CREATE POLICY "trade_market_snapshots_own" ON public."trade_market_snapshots" FOR ALL TO authenticated
            USING (user_id::text = auth.uid()::text) WITH CHECK (user_id::text = auth.uid()::text)''')


def downgrade():
    op.drop_table("trade_market_snapshots")
