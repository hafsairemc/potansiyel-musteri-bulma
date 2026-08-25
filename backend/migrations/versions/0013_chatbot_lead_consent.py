"""Add chatbot lead consent evidence and deduplication."""

import sqlalchemy as sa
from alembic import op

revision = "0013_chatbot_lead_consent"
down_revision = "0012_profile_privileges"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("website_bot_leads", sa.Column("consent_version", sa.String(30), nullable=False, server_default="2026-01"))
    op.add_column("website_bot_leads", sa.Column("consent_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE website_bot_leads SET consent_at = created_at WHERE consent_at IS NULL")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            DELETE FROM website_bot_leads AS older
            USING website_bot_leads AS newer
            WHERE older.bot_id = newer.bot_id AND older.session_id = newer.session_id
              AND (older.created_at < newer.created_at OR (older.created_at = newer.created_at AND older.id < newer.id))
        """)
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("website_bot_leads") as batch:
            batch.alter_column("consent_at", existing_type=sa.DateTime(), nullable=False)
            batch.create_unique_constraint("uq_website_bot_lead_session", ["bot_id", "session_id"])
    else:
        op.alter_column("website_bot_leads", "consent_at", existing_type=sa.DateTime(), nullable=False)
        op.create_unique_constraint("uq_website_bot_lead_session", "website_bot_leads", ["bot_id", "session_id"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("website_bot_leads") as batch:
            batch.drop_constraint("uq_website_bot_lead_session", type_="unique")
            batch.drop_column("consent_at")
            batch.drop_column("consent_version")
    else:
        op.drop_constraint("uq_website_bot_lead_session", "website_bot_leads", type_="unique")
        op.drop_column("website_bot_leads", "consent_at")
        op.drop_column("website_bot_leads", "consent_version")
