import sys
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from routers import visitor_router, auth_router, search_job_router
from routers.product_api import router as product_api_router
from routers.location_router import router as location_router
from routers.search_batch_router import router as search_batch_router
from routers.intelligence_router import router as intelligence_router
from routers.catalog_router import router as catalog_router
from routers.visitor_admin_router import router as visitor_admin_router
from routers.account_router import router as account_router
from routers.health_router import router as health_router
from routers.admin_account_router import router as admin_account_router
from routers.learning_router import router as learning_router
from routers.email_campaign_router import router as email_campaign_router
from routers.demand_post_router import router as demand_post_router
from routers.trade_market_router import router as trade_market_router
from core.rate_limit import add_rate_limiter_to_app
from core.config import settings

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    try:
        dongu = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(dongu)
    except Exception as exc:
        logger.warning("Windows event loop ayarlanamadı: %s", exc)

if os.getenv("SENTRY_DSN"):
    import sentry_sdk
    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), environment=settings.environment, traces_sample_rate=0.1)


@asynccontextmanager
async def uygulama_omru(_: FastAPI):
    logger.info("Pusula API başlatıldı")
    yield


lifespan = uygulama_omru

app = FastAPI(title="Pusula API", version="2.0.0", lifespan=uygulama_omru)

add_rate_limiter_to_app(app)

ham_kokenler = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000,http://localhost:5000,http://127.0.0.1:5000,http://localhost:5500,http://127.0.0.1:5500"
)
izin_verilen_kokenler = [koken.strip() for koken in ham_kokenler.split(",") if koken.strip()]
allowed_origins = izin_verilen_kokenler

app.add_middleware(
    CORSMiddleware,
    allow_origins=izin_verilen_kokenler,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(visitor_router.router, prefix="/api")
app.include_router(visitor_router.events_router, prefix="/api")
app.include_router(product_api_router, prefix="/api")
app.include_router(search_job_router.router, prefix="/api")
app.include_router(location_router, prefix="/api")
app.include_router(search_batch_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(catalog_router, prefix="/api")
app.include_router(visitor_admin_router, prefix="/api")
app.include_router(account_router, prefix="/api")
app.include_router(admin_account_router, prefix="/api")
app.include_router(learning_router, prefix="/api")
app.include_router(email_campaign_router, prefix="/api")
app.include_router(demand_post_router, prefix="/api")
app.include_router(trade_market_router, prefix="/api")

on_yuz_dizini = os.path.join(os.path.dirname(__file__), "..", "frontend", "pusula")
frontend_dir = on_yuz_dizini


@app.get("/{catchall:path}")
def spa_sun(catchall: str):
    if catchall.startswith("api/"):
        raise HTTPException(status_code=404, detail="API uç noktası bulunamadı")

    onbelleksiz_basliklar = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    dosya_yolu = os.path.join(on_yuz_dizini, catchall)
    if os.path.isfile(dosya_yolu) and catchall != "":
        return FileResponse(dosya_yolu, headers=onbelleksiz_basliklar)

    return FileResponse(os.path.join(on_yuz_dizini, "index.html"), headers=onbelleksiz_basliklar)


serve_spa = spa_sun
