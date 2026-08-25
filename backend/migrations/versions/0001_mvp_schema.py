"""Clean Pusula MVP schema, Supabase profile trigger and RLS baseline."""

from alembic import op
import sqlalchemy as sa

revision = "0001_mvp_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "products_v2",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("oem", sa.String(100), nullable=True),
        sa.Column("hs_code", sa.String(50), nullable=True),
        sa.Column("name_tr", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text()), sa.Column("name_de", sa.Text()),
        sa.Column("name_fr", sa.Text()), sa.Column("name_ru", sa.Text()),
        sa.Column("name_es", sa.Text()), sa.Column("name_ar", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("target_languages", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "product_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE")),
        sa.Column("url", sa.Text(), nullable=False),
    )
    op.create_table(
        "product_competitors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE")),
        sa.Column("brand_name", sa.String(255), nullable=False),
    )
    op.create_table(
        "product_industries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE")),
        sa.Column("industry_name", sa.String(255), nullable=False),
    )
    op.create_table(
        "product_target_countries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE")),
        sa.Column("country_name", sa.String(255), nullable=False),
        sa.Column("domain_extension", sa.String(50)),
    )
    op.create_table(
        "search_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "crawler_search_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products_v2.id", ondelete="CASCADE")),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("search_batches.id", ondelete="CASCADE"), index=True),
        sa.Column("start_time", sa.DateTime()), sa.Column("end_time", sa.DateTime()),
        sa.Column("target_country", sa.String(100)),
        sa.Column("search_query", sa.String(255), nullable=False),
        sa.Column("search_engine", sa.String(100), server_default="Google"),
        sa.Column("status", sa.String(50), server_default="PENDING"),
        sa.Column("source", sa.String(50), nullable=False, server_default="search_engine"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100)), sa.Column("error_message", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_url", sa.String(500)),
        sa.Column("total_companies", sa.Integer(), server_default="0"),
        sa.Column("successful_companies", sa.Integer(), server_default="0"),
        sa.Column("failed_companies", sa.Integer(), server_default="0"),
        sa.Column("robots_allowed", sa.Integer(), server_default="0"),
        sa.Column("robots_blocked", sa.Integer(), server_default="0"),
        sa.Column("robots_unknown", sa.Integer(), server_default="0"),
        sa.Column("force_crawl", sa.Boolean(), server_default=sa.false()),
        sa.Column("crawler_logs", sa.JSON()),
    )
    op.create_table(
        "crawler_search_job_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("search_job_id", sa.String(36), sa.ForeignKey("crawler_search_jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("timeout_count", sa.Integer(), server_default="0"),
        sa.Column("captcha_count", sa.Integer(), server_default="0"),
        sa.Column("total_runtime_seconds", sa.Integer(), server_default="0"),
        sa.Column("avg_response_time_ms", sa.Integer(), server_default="0"),
    )
    op.create_table(
        "crawler_companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255)), sa.Column("phone", sa.String(255)),
        sa.Column("email", sa.String(255)), sa.Column("address", sa.Text()),
        sa.Column("country", sa.String(100)), sa.Column("city", sa.String(100)),
        sa.Column("about_us_text", sa.Text()), sa.Column("contact_text", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "crawler_company_websites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("crawler_companies.id", ondelete="CASCADE")),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50), server_default="PENDING"),
        sa.Column("last_scraped_at", sa.DateTime()),
    )
    op.create_table(
        "crawler_products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
    )
    op.create_table(
        "crawler_company_products",
        sa.Column("company_id", sa.String(36), sa.ForeignKey("crawler_companies.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("crawler_products.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "crawler_search_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("search_job_id", sa.String(36), sa.ForeignKey("crawler_search_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("crawler_companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("position", sa.Integer()),
        sa.Column("source", sa.String(50), nullable=False, server_default="search_engine"),
        sa.Column("platform", sa.String(100)), sa.Column("search_query", sa.Text()),
        sa.Column("sector_match", sa.String(20), nullable=False, server_default="main"),
        sa.Column("customer_type", sa.String(50)),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("match_reason", sa.Text()),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("search_job_id", "source_url", name="uq_job_source_url"),
    )
    op.create_table(
        "search_exports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("search_batches.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("file_url", sa.Text()), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "visitors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("permission", sa.String(50)), sa.Column("country", sa.String(100)),
        sa.Column("city", sa.String(100)), sa.Column("formatted_address", sa.Text()),
        sa.Column("latitude", sa.Float()), sa.Column("longitude", sa.Float()),
        sa.Column("ip", sa.String(100)), sa.Column("operator", sa.String(255)),
        sa.Column("detection_method", sa.String(50)), sa.Column("confidence", sa.Float()),
        sa.Column("retention_until", sa.DateTime(), index=True),
        sa.Column("created_at", sa.DateTime()),
    )

    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    op.execute("""
    CREATE TABLE IF NOT EXISTS public.profiles (
      id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
      company_name text NOT NULL DEFAULT 'Pusula', full_name text,
      role text NOT NULL DEFAULT 'user', plan text NOT NULL DEFAULT 'starter',
      is_active boolean NOT NULL DEFAULT true,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE OR REPLACE FUNCTION public.handle_new_user()
    RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
    BEGIN
      INSERT INTO public.profiles (id, full_name)
      VALUES (new.id, COALESCE(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', new.email))
      ON CONFLICT (id) DO NOTHING;
      RETURN new;
    END; $$;
    DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
    CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users
      FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
    INSERT INTO public.profiles (id, full_name)
      SELECT id, COALESCE(raw_user_meta_data->>'full_name', raw_user_meta_data->>'name', email)
      FROM auth.users ON CONFLICT (id) DO NOTHING;
    """)

    for table in ("products_v2", "search_batches", "crawler_search_jobs", "search_exports"):
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'''CREATE POLICY "{table}_own" ON public."{table}" FOR ALL TO authenticated
          USING (user_id::text = auth.uid()::text) WITH CHECK (user_id::text = auth.uid()::text)''')

    op.execute("ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY profiles_own ON public.profiles FOR SELECT TO authenticated USING (id = auth.uid())")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON public.profiles FROM authenticated, anon")
    op.execute("GRANT SELECT ON public.profiles TO authenticated")

    for table in ("product_images", "product_competitors", "product_industries", "product_target_countries"):
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'''CREATE POLICY "{table}_own" ON public."{table}" FOR SELECT TO authenticated USING (
          EXISTS (SELECT 1 FROM public.products_v2 p WHERE p.id = "{table}".product_id AND p.user_id::text = auth.uid()::text))''')
    op.execute("ALTER TABLE public.crawler_search_results ENABLE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY crawler_search_results_own ON public.crawler_search_results FOR SELECT TO authenticated USING (
      EXISTS (SELECT 1 FROM public.crawler_search_jobs j WHERE j.id = search_job_id AND j.user_id::text = auth.uid()::text))""")
    op.execute("ALTER TABLE public.crawler_companies ENABLE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY crawler_companies_own ON public.crawler_companies FOR SELECT TO authenticated USING (
      EXISTS (SELECT 1 FROM public.crawler_search_results r JOIN public.crawler_search_jobs j ON j.id = r.search_job_id
              WHERE r.company_id = crawler_companies.id AND j.user_id::text = auth.uid()::text))""")
    for table in ("visitors", "crawler_company_websites", "crawler_search_job_metrics", "crawler_products", "crawler_company_products"):
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')

    op.execute("""
    INSERT INTO storage.buckets (id, name, public) VALUES ('product-images', 'product-images', false)
      ON CONFLICT (id) DO UPDATE SET public = false;
    INSERT INTO storage.buckets (id, name, public) VALUES ('reports', 'reports', false)
      ON CONFLICT (id) DO UPDATE SET public = false;
    DROP POLICY IF EXISTS pusula_storage_select ON storage.objects;
    DROP POLICY IF EXISTS pusula_storage_insert ON storage.objects;
    DROP POLICY IF EXISTS pusula_storage_delete ON storage.objects;
    CREATE POLICY pusula_storage_select ON storage.objects FOR SELECT TO authenticated
      USING (bucket_id IN ('product-images','reports') AND (storage.foldername(name))[1] = auth.uid()::text);
    CREATE POLICY pusula_storage_insert ON storage.objects FOR INSERT TO authenticated
      WITH CHECK (bucket_id IN ('product-images','reports') AND (storage.foldername(name))[1] = auth.uid()::text);
    CREATE POLICY pusula_storage_delete ON storage.objects FOR DELETE TO authenticated
      USING (bucket_id IN ('product-images','reports') AND (storage.foldername(name))[1] = auth.uid()::text);
    """)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users")
        op.execute("DROP FUNCTION IF EXISTS public.handle_new_user()")
        for policy in ("pusula_storage_select", "pusula_storage_insert", "pusula_storage_delete"):
            op.execute(f"DROP POLICY IF EXISTS {policy} ON storage.objects")
        op.execute("DROP TABLE IF EXISTS public.profiles")
    for table in (
        "visitors", "search_exports", "crawler_search_results", "crawler_company_products",
        "crawler_products", "crawler_company_websites", "crawler_companies",
        "crawler_search_job_metrics", "crawler_search_jobs", "search_batches",
        "product_target_countries", "product_industries", "product_competitors",
        "product_images", "products_v2",
    ):
        op.drop_table(table)
