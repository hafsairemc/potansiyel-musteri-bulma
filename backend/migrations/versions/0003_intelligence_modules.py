"""Add RFQ, contact, fair and assistant modules."""

from alembic import op
import sqlalchemy as sa

revision = "0003_intelligence_modules"
down_revision = "0002_search_quality"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rfq_searches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_country", sa.String(100), server_default="Türkiye"),
        sa.Column("date_from", sa.DateTime()),
        sa.Column("status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100)), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "rfq_opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rfq_search_id", sa.String(36), sa.ForeignKey("rfq_searches.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False), sa.Column("buyer_name", sa.String(255)),
        sa.Column("country", sa.String(100)), sa.Column("quantity", sa.String(100)),
        sa.Column("deadline", sa.String(100)), sa.Column("description", sa.Text()),
        sa.Column("platform", sa.String(100)), sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50), server_default="indexed_public"),
        sa.Column("access_status", sa.String(30), nullable=False, server_default="public"),
        sa.Column("relevance_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freshness_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("match_reason", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("rfq_search_id", "source_url", name="uq_rfq_source"),
    )
    op.create_table(
        "contact_discoveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("crawler_companies.id", ondelete="SET NULL")),
        sa.Column("company_name", sa.String(255), nullable=False), sa.Column("domain", sa.String(255)),
        sa.Column("status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100)), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "company_contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contact_discovery_id", sa.String(36), sa.ForeignKey("contact_discoveries.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("full_name", sa.String(255), nullable=False), sa.Column("role", sa.String(255)),
        sa.Column("company_name", sa.String(255), nullable=False), sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(100)), sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50), server_default="indexed_public"),
        sa.Column("access_status", sa.String(30), nullable=False, server_default="public"),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("match_reason", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("contact_discovery_id", "source_url", "full_name", name="uq_contact_source_name"),
    )
    op.create_table(
        "fair_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("column_mapping", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="UPLOADED"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100)), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "fair_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("fair_analysis_id", sa.String(36), sa.ForeignKey("fair_analyses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("row_number", sa.Integer(), nullable=False), sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("website", sa.Text()), sa.Column("country", sa.String(100)), sa.Column("city", sa.String(100)),
        sa.Column("sector", sa.String(255)), sa.Column("description", sa.Text()),
        sa.Column("email", sa.String(255)), sa.Column("phone", sa.String(100)),
        sa.Column("access_status", sa.String(30), nullable=False, server_default="public"),
        sa.Column("relevance_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("buyer_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("matched_terms", sa.JSON(), nullable=False), sa.Column("match_reason", sa.Text()),
        sa.Column("original_data", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("title", sa.String(255), server_default="Pusula Asistanı"),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="fallback"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    parents = ("rfq_searches", "contact_discoveries", "fair_analyses", "assistant_conversations")
    for table in parents:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'''CREATE POLICY "{table}_own" ON public."{table}" FOR ALL TO authenticated
          USING (user_id::text = auth.uid()::text) WITH CHECK (user_id::text = auth.uid()::text)''')
    children = {
        "rfq_opportunities": ("rfq_searches", "rfq_search_id"),
        "company_contacts": ("contact_discoveries", "contact_discovery_id"),
        "fair_entries": ("fair_analyses", "fair_analysis_id"),
        "assistant_messages": ("assistant_conversations", "conversation_id"),
    }
    for table, (parent, fk) in children.items():
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'''CREATE POLICY "{table}_own" ON public."{table}" FOR SELECT TO authenticated USING (
          EXISTS (SELECT 1 FROM public."{parent}" p WHERE p.id = "{table}"."{fk}" AND p.user_id::text = auth.uid()::text))''')


def downgrade():
    for table in ("assistant_messages", "assistant_conversations", "fair_entries", "fair_analyses", "company_contacts", "contact_discoveries", "rfq_opportunities", "rfq_searches"):
        op.drop_table(table)
