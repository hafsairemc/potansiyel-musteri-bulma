"""Prevent users from changing their own role or plan."""

from alembic import op

revision = "0012_profile_privileges"
down_revision = "0011_required_ownership"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS profiles_update_own ON public.profiles")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON public.profiles FROM authenticated, anon")
    op.execute("GRANT SELECT ON public.profiles TO authenticated")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("GRANT UPDATE ON public.profiles TO authenticated")
    op.execute("""
        CREATE POLICY profiles_update_own ON public.profiles FOR UPDATE TO authenticated
        USING (id = auth.uid()) WITH CHECK (id = auth.uid())
    """)
