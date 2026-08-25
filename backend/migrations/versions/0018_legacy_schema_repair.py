"""Repair columns from databases created before the Alembic baseline."""

import sqlalchemy as sa
from alembic import op

revision = "0018_legacy_schema_repair"
down_revision = "0017_fair_analysis_metrics"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _repair_products(inspector, bind.dialect.name)
    _repair_jobs(inspector, bind.dialect.name)
    _repair_companies(inspector)
    _repair_results(inspector, bind.dialect.name)


def _repair_products(inspector, dialect: str) -> None:
    columns = {
        column["name"]: column for column in inspector.get_columns("products_v2")
    }
    additions = []
    if "description" not in columns:
        additions.append(sa.Column("description", sa.Text(), nullable=True))
    if "created_at" not in columns:
        additions.append(sa.Column("created_at", sa.DateTime(), nullable=True))
    relaxed = [
        name
        for name in ("oem", "hs_code", "name_en")
        if name in columns and not columns[name]["nullable"]
    ]
    if dialect == "sqlite" and (additions or relaxed):
        with op.batch_alter_table("products_v2") as batch:
            for column in additions:
                batch.add_column(column)
            for name in relaxed:
                batch.alter_column(
                    name, existing_type=columns[name]["type"], nullable=True
                )
        return
    for column in additions:
        op.add_column("products_v2", column)
    for name in relaxed:
        op.alter_column(
            "products_v2", name, existing_type=columns[name]["type"], nullable=True
        )


def _repair_jobs(inspector, dialect: str) -> None:
    columns = {
        column["name"]: column
        for column in inspector.get_columns("crawler_search_jobs")
    }
    defaults = {"source": "search_engine", "progress": 0, "attempt_count": 0}
    for name, value in defaults.items():
        if name in columns and columns[name]["nullable"]:
            literal = f"'{value}'" if isinstance(value, str) else str(value)
            op.execute(
                f"UPDATE crawler_search_jobs SET {name} = {literal} WHERE {name} IS NULL"
            )
    add_batch = "batch_id" not in columns
    required = [
        name for name in defaults if name in columns and columns[name]["nullable"]
    ]
    if dialect == "sqlite" and (add_batch or required):
        with op.batch_alter_table("crawler_search_jobs") as batch:
            if add_batch:
                batch.add_column(
                    sa.Column(
                        "batch_id",
                        sa.String(36),
                        sa.ForeignKey(
                            "search_batches.id",
                            name="fk_crawler_search_jobs_batch_id",
                            ondelete="CASCADE",
                        ),
                        nullable=True,
                    )
                )
            for name in required:
                batch.alter_column(
                    name, existing_type=columns[name]["type"], nullable=False
                )
        return
    if add_batch:
        op.add_column(
            "crawler_search_jobs",
            sa.Column(
                "batch_id",
                sa.String(36),
                sa.ForeignKey(
                    "search_batches.id",
                    name="fk_crawler_search_jobs_batch_id",
                    ondelete="CASCADE",
                ),
                nullable=True,
            ),
        )
    for name in required:
        op.alter_column(
            "crawler_search_jobs",
            name,
            existing_type=columns[name]["type"],
            nullable=False,
        )


def _repair_companies(inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns("crawler_companies")}
    if "city" not in columns:
        op.add_column(
            "crawler_companies", sa.Column("city", sa.String(100), nullable=True)
        )


def _repair_results(inspector, dialect: str) -> None:
    columns = {
        column["name"]: column
        for column in inspector.get_columns("crawler_search_results")
    }
    defaults = {
        "source": "search_engine",
        "sector_match": "main",
        "score": 0,
        "confidence_score": 0,
        "collected_at": "CURRENT_TIMESTAMP",
    }
    for name, value in defaults.items():
        if name in columns and columns[name]["nullable"]:
            literal = (
                value
                if value == "CURRENT_TIMESTAMP"
                else (f"'{value}'" if isinstance(value, str) else str(value))
            )
            op.execute(
                f"UPDATE crawler_search_results SET {name} = {literal} WHERE {name} IS NULL"
            )
    add_platform = "platform" not in columns
    required = [
        name for name in defaults if name in columns and columns[name]["nullable"]
    ]
    if dialect == "sqlite" and (add_platform or required):
        with op.batch_alter_table("crawler_search_results") as batch:
            if add_platform:
                batch.add_column(sa.Column("platform", sa.String(100), nullable=True))
            for name in required:
                batch.alter_column(
                    name, existing_type=columns[name]["type"], nullable=False
                )
        return
    if add_platform:
        op.add_column(
            "crawler_search_results",
            sa.Column("platform", sa.String(100), nullable=True),
        )
    for name in required:
        op.alter_column(
            "crawler_search_results",
            name,
            existing_type=columns[name]["type"],
            nullable=False,
        )


def downgrade():
    pass
