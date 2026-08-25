import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


@dataclass(frozen=True)
class DatabaseUrls:
    sync: str
    async_: str
    async_connect_args: dict[str, Any] = field(default_factory=dict)


def _sema_duzelt(adres: str) -> str:
    if adres.startswith("postgres://"):
        return "postgresql://" + adres.removeprefix("postgres://")
    return adres


def _asenkron_sqlite_adresi(adres: str) -> str:
    return (
        adres.replace("sqlite+pysqlite://", "sqlite+aiosqlite://", 1)
        .replace("sqlite://", "sqlite+aiosqlite://", 1)
    )


def resolve_database_urls(
    uzak_baglanti: bool,
    senkron_url: str | None,
    asenkron_url: str | None,
) -> DatabaseUrls:
    if not uzak_baglanti:
        yerel_senkron = (
            senkron_url.strip()
            if senkron_url and senkron_url.strip().startswith("sqlite")
            else "sqlite:///./pusula.db"
        )
        yerel_asenkron = (
            asenkron_url.strip()
            if asenkron_url and asenkron_url.strip().startswith("sqlite+")
            else _asenkron_sqlite_adresi(yerel_senkron)
        )
        return DatabaseUrls(
            sync=yerel_senkron,
            async_=yerel_asenkron,
            async_connect_args={"check_same_thread": False},
        )

    if not senkron_url or not senkron_url.strip():
        raise RuntimeError("USE_REMOTE_DB=true olduğunda DATABASE_URL zorunludur")

    temiz_senkron = make_url(_sema_duzelt(senkron_url.strip()))
    if temiz_senkron.get_backend_name() != "postgresql":
        raise RuntimeError("Uzak veritabanı PostgreSQL olmalıdır")

    if temiz_senkron.drivername == "postgresql+asyncpg":
        temiz_senkron = temiz_senkron.set(drivername="postgresql+psycopg2")

    hedef_asenkron = (asenkron_url or senkron_url).strip()
    temiz_asenkron = make_url(_sema_duzelt(hedef_asenkron))
    temiz_asenkron = temiz_asenkron.set(drivername="postgresql+asyncpg")

    parametreler = dict(temiz_asenkron.query)
    ssl_modu = parametreler.pop("sslmode", parametreler.pop("ssl", None))
    uygulama_adi = parametreler.pop("application_name", None)
    temiz_asenkron = temiz_asenkron.set(query=parametreler)

    baglanti_ayarlari: dict[str, Any] = {"statement_cache_size": 0}
    if ssl_modu and str(ssl_modu).lower() not in {"disable", "false", "0"}:
        baglanti_ayarlari["ssl"] = True
    if uygulama_adi:
        baglanti_ayarlari["server_settings"] = {"application_name": str(uygulama_adi)}

    return DatabaseUrls(
        sync=temiz_senkron.render_as_string(hide_password=False),
        async_=temiz_asenkron.render_as_string(hide_password=False),
        async_connect_args=baglanti_ayarlari,
    )


veritabani_adreslerini_coz = resolve_database_urls

uzak_veritabani_kullan = os.getenv("USE_REMOTE_DB", "false").lower() == "true"
db_adresleri = resolve_database_urls(
    uzak_veritabani_kullan,
    os.getenv("DATABASE_URL"),
    os.getenv("ASYNC_DATABASE_URL"),
)

DATABASE_URL = db_adresleri.sync
ASYNC_DATABASE_URL = db_adresleri.async_

baglanti_ayarlari = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=baglanti_ayarlari)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

asenkron_baglanti_ayarlari = {
    "echo": False,
    "connect_args": db_adresleri.async_connect_args,
}
async_engine = create_async_engine(ASYNC_DATABASE_URL, **asenkron_baglanti_ayarlari)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=async_engine,
    class_=AsyncSession,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session


veritabani_al = get_db
asenkron_veritabani_al = get_async_db
