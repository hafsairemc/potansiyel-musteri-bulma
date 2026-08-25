"""Require ownership for products and search jobs."""

import sqlalchemy as sa
from alembic import op

revision = "0011_required_ownership"
down_revision = "0010_email_replies"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_columns = {column["name"] for column in inspector.get_columns("products_v2")}
    job_columns = {column["name"] for column in inspector.get_columns("crawler_search_jobs")}
    if "user_id" not in product_columns:
        op.add_column("products_v2", sa.Column("user_id", sa.String(36), nullable=True))
    if "user_id" not in job_columns:
        op.add_column("crawler_search_jobs", sa.Column("user_id", sa.String(36), nullable=True))
    op.execute("UPDATE products_v2 SET user_id = 'legacy-unowned' WHERE user_id IS NULL")
    if "batch_id" in job_columns:
        op.execute("""
            UPDATE crawler_search_jobs AS job
            SET user_id = COALESCE(
                (SELECT batch.user_id FROM search_batches AS batch WHERE batch.id = job.batch_id),
                (SELECT product.user_id FROM products_v2 AS product WHERE product.id = job.product_id),
                'legacy-unowned'
            )
            WHERE job.user_id IS NULL
        """)
    else:
        op.execute("""
            UPDATE crawler_search_jobs AS job
            SET user_id = COALESCE(
                (SELECT product.user_id FROM products_v2 AS product WHERE product.id = job.product_id),
                'legacy-unowned'
            )
            WHERE job.user_id IS NULL
        """)
    op.execute("UPDATE crawler_search_jobs SET user_id = 'legacy-unowned' WHERE user_id IS NULL")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("products_v2") as batch:
            batch.alter_column("user_id", existing_type=sa.String(36), nullable=False)
        with op.batch_alter_table("crawler_search_jobs") as batch:
            batch.alter_column("user_id", existing_type=sa.String(36), nullable=False)
    else:
        op.alter_column("products_v2", "user_id", existing_type=sa.String(36), nullable=False)
        op.alter_column("crawler_search_jobs", "user_id", existing_type=sa.String(36), nullable=False)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("crawler_search_jobs") as batch:
            batch.alter_column("user_id", existing_type=sa.String(36), nullable=True)
        with op.batch_alter_table("products_v2") as batch:
            batch.alter_column("user_id", existing_type=sa.String(36), nullable=True)
    else:
        op.alter_column("crawler_search_jobs", "user_id", existing_type=sa.String(36), nullable=True)
        op.alter_column("products_v2", "user_id", existing_type=sa.String(36), nullable=True)
