import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _to_bool(degisken_adi: str, varsayilan: bool = False) -> bool:
    deger = os.getenv(degisken_adi, str(varsayilan)).strip().lower()
    return deger in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    dev_mode: bool = _to_bool("DEV_MODE", False)
    auto_create_schema: bool = _to_bool("AUTO_CREATE_SCHEMA", False)
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_publishable_key: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    supabase_secret_key: str = os.getenv("SUPABASE_SECRET_KEY", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    product_images_bucket: str = os.getenv("PRODUCT_IMAGES_BUCKET", "product-images")
    reports_bucket: str = os.getenv("REPORTS_BUCKET", "reports")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "8"))


settings = Settings()
