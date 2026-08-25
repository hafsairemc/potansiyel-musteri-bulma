import os
from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import text

from core.config import settings
from core.database import AsyncSessionLocal
from core.security import get_current_user
from services.capability_service import CapabilityService

router = APIRouter(tags=["Health"])


@router.get("/health")
def saglik_kontrolu():
    return {"status": "ok", "environment": settings.environment}


@router.get("/capabilities")
def yetenek_ozeti(_: dict = Depends(get_current_user)):
    return CapabilityService().summary()


@router.get("/ready")
async def hazirlik_kontrolu():
    kontroller = {"database": "unavailable", "queue": "not_required"}

    try:
        async with AsyncSessionLocal() as oturum:
            await oturum.execute(text("SELECT 1"))
        kontroller["database"] = "ok"
    except Exception:
        raise HTTPException(503, detail={"status": "not_ready", "checks": kontroller})

    if os.getenv("TASK_QUEUE_MODE", "celery").lower() == "celery":
        istemci = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            await istemci.ping()
            kontroller["queue"] = "ok"
        except Exception:
            kontroller["queue"] = "unavailable"
            raise HTTPException(503, detail={"status": "not_ready", "checks": kontroller})
        finally:
            await istemci.aclose()

    return {"status": "ready", "checks": kontroller}


health = saglik_kontrolu
capabilities = yetenek_ozeti
readiness = hazirlik_kontrolu
