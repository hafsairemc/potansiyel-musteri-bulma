import logging
from supabase import Client, create_client
from core.config import settings

logger = logging.getLogger(__name__)

try:
    kamusal_supabase: Client | None = (
        create_client(settings.supabase_url, settings.supabase_publishable_key)
        if settings.supabase_url and settings.supabase_publishable_key else None
    )
    yonetici_supabase: Client | None = (
        create_client(settings.supabase_url, settings.supabase_secret_key)
        if settings.supabase_url and settings.supabase_secret_key else None
    )
except Exception as exc:
    logger.exception("Supabase istemcisi başlatılamadı: %s", exc)
    kamusal_supabase = None
    yonetici_supabase = None

public_supabase = kamusal_supabase
admin_supabase = yonetici_supabase
supabase = kamusal_supabase
