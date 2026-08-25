import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from core.rate_limit import limiter
from models.schemas import LocationRequest
from services.geocoding_service import GeocodingService
from services.ip_privacy_service import anonymize_ip, resolve_client_ip
from services.ip_service import IpService
from services.places_service import PlacesService
from services.visitor_event_service import VisitorEventService

router = APIRouter(prefix="/visitor", tags=["visitor"])
events_router = APIRouter(prefix="/visitor-events", tags=["visitor"])
logger = logging.getLogger(__name__)


@router.post("/location")
@events_router.post("")
@limiter.limit("10/minute")
def konum_kaydet(
    req: LocationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    try:
        ulke = req.country
        sehir = req.city
        enlem = req.latitude
        boylam = req.longitude
        bulunan_firma = None

        kullanici_ip = resolve_client_ip(request)

        if not req.permission:
            servis = VisitorEventService()
            eklenen_id, _ = servis.save({
                "permission": "false",
                "detection_method": "none",
                "confidence": 0.0,
            })
            if eklenen_id:
                return {
                    "message": "Konum izni tercihi kaydedildi.",
                    "id": eklenen_id,
                    "company": None,
                }
            raise HTTPException(status_code=503, detail="İzin tercihi kaydedilemedi")

        if enlem is None or boylam is None:
            ip_verisi = IpService.get_location_from_ip(kullanici_ip)
            if ip_verisi:
                ulke = ip_verisi["country"]
                sehir = ip_verisi["city"]
                enlem = ip_verisi["latitude"]
                boylam = ip_verisi["longitude"]
        else:
            cografi_bilgi = GeocodingService.get_city_and_country(enlem, boylam)
            ulke = cografi_bilgi["country"]
            sehir = cografi_bilgi["city"]
            bulunan_firma = PlacesService.find_nearby_company(enlem, boylam)

        ziyaretci_verisi = {
            "permission": "true" if req.permission else "false",
            "country": ulke,
            "city": sehir,
            "latitude": enlem,
            "longitude": boylam,
            "ip": anonymize_ip(kullanici_ip),
            "operator": bulunan_firma,
            "detection_method": (
                "gps_poi"
                if req.permission and enlem is not None and boylam is not None
                else "ip_fallback"
            ),
            "confidence": 0.7 if bulunan_firma else 0.3,
        }

        servis = VisitorEventService()
        eklenen_id, olay = servis.save(ziyaretci_verisi)
        if eklenen_id:
            background_tasks.add_task(servis.notify, olay)
            return {
                "message": "Ziyaretçi bilgileri başarıyla kaydedildi.",
                "id": eklenen_id,
                "company": bulunan_firma,
            }
        raise HTTPException(status_code=503, detail="Ziyaretçi kaydı oluşturulamadı")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Ziyaretçi konumu işlenemedi: %s", exc)
        raise HTTPException(status_code=503, detail="Konum işlemi tamamlanamadı") from exc


@events_router.delete("/{visitor_id}", status_code=204)
@limiter.limit("10/minute")
def ziyaretci_kaydini_sil(visitor_id: str, request: Request):
    try:
        silindi = VisitorEventService().storage.delete_by_id(visitor_id)
    except Exception as exc:
        logger.warning("Ziyaretçi kaydı silinemedi: %s", exc)
        raise HTTPException(status_code=503, detail="Ziyaretçi kaydı silinemedi") from exc

    if not silindi:
        raise HTTPException(status_code=404, detail="Ziyaretçi kaydı bulunamadı")
    return Response(status_code=204)


save_location = konum_kaydet
delete_visitor_event = ziyaretci_kaydini_sil
