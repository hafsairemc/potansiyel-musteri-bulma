"""Add server-verified learning attempts."""

import sqlalchemy as sa
from alembic import op

revision = "0021_learning_attempts"
down_revision = "0020_email_delivery_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learning_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("lesson_key", sa.String(80), nullable=False),
        sa.Column("answer_index", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_learning_attempts_user_id",
        "learning_attempts",
        ["user_id"],
    )
    op.create_index(
        "ix_learning_attempts_lesson_key",
        "learning_attempts",
        ["lesson_key"],
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            'ALTER TABLE public."learning_attempts" ENABLE ROW LEVEL SECURITY'
        )
        op.execute(
            '''CREATE POLICY "learning_attempts_own" ON public."learning_attempts"
            FOR SELECT TO authenticated USING (user_id::text = auth.uid()::text)'''
        )
        op.execute(
            "REVOKE INSERT, UPDATE, DELETE ON public.learning_attempts "
            "FROM authenticated, anon"
        )


def downgrade():
    op.drop_table("learning_attempts")
