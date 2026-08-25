"""Add audited central account control."""

import sqlalchemy as sa
from alembic import op

revision = "0007_admin_control"
down_revision = "0006_demand_publication"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_user_id", sa.String(36), nullable=False, index=True),
        sa.Column("target_user_id", sa.String(36), nullable=False, index=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE public."admin_actions" ENABLE ROW LEVEL SECURITY')
        op.execute('''CREATE POLICY "admin_actions_admin_read" ON public."admin_actions" FOR SELECT TO authenticated USING (
            EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'admin' AND p.is_active = true))''')


def downgrade():
    op.drop_table("admin_actions")
