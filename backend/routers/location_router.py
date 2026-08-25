import logging
import os
from fastapi import APIRouter, BackgroundTasks, Query, Request
from pydantic import BaseModel

from core.rate_limit import limiter
from schemas.location_schema import LocationDetectionResult
from services.ip_privacy_service import anonymize_ip, resolve_client_ip
from services.location.location_orchestrator import get_location_orchestrator
from services.visitor_event_service import VisitorEventService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/location", tags=["Location Detection"])


class LocationDetectRequest(BaseModel):
    permission: bool = False
    latitude: float | None = None
    longitude: float | None = None


class LocationHealthResponse(BaseModel):
    overpass: str
    here: str
    radar: str
    ip_api: str


KonumTespitIstegi = LocationDetectRequest
KonumSaglikYaniti = LocationHealthResponse


def _ziyaretciyi_kaydet(
    sonuc: LocationDetectionResult,
    ip_adresi: str,
    arkaplan_gorevleri: BackgroundTasks,
) -> str | None:
    try:
        if not sonuc.permission_granted:
            ziyaretci_id, _ = VisitorEventService().save({
                "permission": "false",
                "detection_method": "none",
                "confidence": 0.0,
            })
            return ziyaretci_id

        firma_adi = None
        if sonuc.poi:
            firma_adi = sonuc.poi.name
        elif sonuc.ip_data and sonuc.ip_data.is_corporate:
            firma_adi = sonuc.ip_data.org

        guven_skoru = (
            sonuc.poi.confidence
            if sonuc.poi
            else (0.6 if sonuc.ip_data and sonuc.ip_data.is_corporate else 0.3)
        )

        ziyaretci_verisi = {
            "permission": "true" if sonuc.permission_granted else "false",
            "country": sonuc.country,
            "city": sonuc.city,
            "formatted_address": sonuc.formatted_address,
            "latitude": sonuc.latitude,
            "longitude": sonuc.longitude,
            "ip": anonymize_ip(ip_adresi),
            "operator": firma_adi,
            "detection_method": sonuc.detection_method,
            "confidence": guven_skoru,
        }
        servis = VisitorEventService()
        ziyaretci_id, olay = servis.save(ziyaretci_verisi)
        if ziyaretci_id:
            arkaplan_gorevleri.add_task(servis.notify, olay)
        return ziyaretci_id
    except Exception as exc:
        logger.warning("Ziyaretçi kaydetme hatası: %s", exc)
        return None


_try_save_visitor = _ziyaretciyi_kaydet


@router.post("/detect", response_model=LocationDetectionResult)
@limiter.limit("10/minute")
def konum_tespit_et_post(
    body: LocationDetectRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> LocationDetectionResult:
    istemci_ip = resolve_client_ip(request)
    orkestrator = get_location_orchestrator()
    sonuc = orkestrator.detect(
        lat=body.latitude,
        lon=body.longitude,
        permission_granted=body.permission,
        ip_address=istemci_ip,
    )
    sonuc.id = _ziyaretciyi_kaydet(sonuc, istemci_ip, background_tasks)
    return sonuc


@router.get("/detect", response_model=LocationDetectionResult)
@limiter.limit("10/minute")
def konum_tespit_et_get(
    request: Request,
    background_tasks: BackgroundTasks,
    permission: bool = Query(False),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
) -> LocationDetectionResult:
    istemci_ip = resolve_client_ip(request)
    orkestrator = get_location_orchestrator()
    sonuc = orkestrator.detect(
        lat=lat,
        lon=lon,
        permission_granted=permission,
        ip_address=istemci_ip,
    )
    sonuc.id = _ziyaretciyi_kaydet(sonuc, istemci_ip, background_tasks)
    return sonuc


@router.get("/health")
@limiter.limit("30/minute")
def konum_saglik_durumu(request: Request):
    return {
        "overpass": "active (free, always on)",
        "here": "configured" if os.getenv("HERE_API_KEY") else "disabled (set HERE_API_KEY)",
        "radar": "configured" if os.getenv("RADAR_API_KEY") else "disabled (set RADAR_API_KEY)",
        "ip_api": "active (free, 45req/min)",
        "ipapi_co": "active (free, 1000req/day)",
    }


detect_location = konum_tespit_et_post
detect_location_get = konum_tespit_et_get
location_health = konum_saglik_durumu
