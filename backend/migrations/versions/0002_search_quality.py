"""Add product search profile and explainable result scores."""

from alembic import op
import sqlalchemy as sa

revision = "0002_search_quality"
down_revision = "0001_mvp_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products_v2", sa.Column("search_profile", sa.JSON(), nullable=True))
    op.execute("UPDATE products_v2 SET search_profile = '{}' WHERE search_profile IS NULL")
    op.add_column("crawler_search_results", sa.Column("relevance_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawler_search_results", sa.Column("buyer_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawler_search_results", sa.Column("matched_terms", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("crawler_search_results", sa.Column("category_path", sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column("crawler_search_results", "category_path")
    op.drop_column("crawler_search_results", "matched_terms")
    op.drop_column("crawler_search_results", "buyer_score")
    op.drop_column("crawler_search_results", "relevance_score")
    op.drop_column("products_v2", "search_profile")
