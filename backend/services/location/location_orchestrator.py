import logging
import os

from services.location.interfaces import IPoiProvider, IIpProvider
from services.location.overpass_poi_service import OverpassPoiService
from services.location.here_poi_service import HerePoiService
from services.location.radar_poi_service import RadarPoiService
from services.location.ip_detection_service import IpApiService, IpapiCoService
from services.geocoding_service import GeocodingService
from schemas.location_schema import LocationDetectionResult

logger = logging.getLogger(__name__)


def _mekan_zinciri_olustur() -> list[IPoiProvider]:
    zincir: list[IPoiProvider] = []

    if os.getenv("HERE_API_KEY"):
        zincir.append(HerePoiService(radius_m=100))
        logger.debug("POI zinciri: HERE eklendi.")

    if os.getenv("RADAR_API_KEY"):
        zincir.append(RadarPoiService(radius_m=100))
        logger.debug("POI zinciri: Radar eklendi.")

    zincir.append(OverpassPoiService(radius_m=50))
    logger.debug("POI zinciri: Overpass eklendi.")

    return zincir


_build_poi_chain = _mekan_zinciri_olustur


def _ip_zinciri_olustur() -> list[IIpProvider]:
    return [
        IpApiService(),
        IpapiCoService(),
    ]


_build_ip_chain = _ip_zinciri_olustur


class KonumOrkestratoru:
    def __init__(
        self,
        poi_providers: list[IPoiProvider] | None = None,
        ip_providers: list[IIpProvider] | None = None,
    ):
        self._poi_providers = poi_providers or _mekan_zinciri_olustur()
        self._ip_providers = ip_providers or _ip_zinciri_olustur()

    def tespit_et(
        self,
        lat: float | None,
        lon: float | None,
        permission_granted: bool,
        ip_address: str | None = None,
    ) -> LocationDetectionResult:
        gps_mevcut_mu = lat is not None and lon is not None

        if not permission_granted:
            return LocationDetectionResult(
                detection_method="none",
                gps_available=False,
                permission_granted=False,
                error="Konum izni verilmedi.",
            )

        if gps_mevcut_mu:
            poi, mekan_saglayici = self._mekan_zincirini_dene(lat, lon)
            geo = self._geocoding_dene(lat, lon)

            if poi:
                logger.info(
                    "Konum tespiti BAŞARILI [GPS/POI | sağlayıcı=%s | işletme=%s]",
                    mekan_saglayici, poi.name
                )
                return LocationDetectionResult(
                    detection_method="gps_poi",
                    gps_available=True,
                    permission_granted=True,
                    poi=poi,
                    latitude=lat,
                    longitude=lon,
                    country=geo.get("country"),
                    city=geo.get("city"),
                    formatted_address=geo.get("formatted_address"),
                    provider=mekan_saglayici,
                )

            if geo.get("country") or geo.get("formatted_address"):
                logger.info(
                    "GPS var, POI yok → Geocoding ile tamamlandı [kaynak=%s]",
                    geo.get("source")
                )
                return LocationDetectionResult(
                    detection_method="gps_poi",
                    gps_available=True,
                    permission_granted=True,
                    latitude=lat,
                    longitude=lon,
                    country=geo.get("country"),
                    city=geo.get("city"),
                    formatted_address=geo.get("formatted_address"),
                    provider=geo.get("source"),
                )

            logger.info("GPS var ama ne POI ne geocoding sonuç verdi → IP fallback.")

        ip_sonucu = self._ip_zincirini_dene(ip_address)

        if ip_sonucu:
            logger.info(
                "Konum tespiti FALLBACK [IP | org=%s | kurumsal=%s]",
                ip_sonucu.org, ip_sonucu.is_corporate
            )
            return LocationDetectionResult(
                detection_method="ip_fallback",
                gps_available=gps_mevcut_mu,
                permission_granted=permission_granted,
                ip_data=ip_sonucu,
                latitude=ip_sonucu.latitude,
                longitude=ip_sonucu.longitude,
                country=ip_sonucu.country,
                city=ip_sonucu.city,
                provider=ip_sonucu.ip,
            )

        logger.warning("Hem GPS/POI hem de IP tespiti başarısız oldu.")
        return LocationDetectionResult(
            detection_method="none",
            gps_available=gps_mevcut_mu,
            permission_granted=permission_granted,
            error="Konum ve kurumsal ağ tespit edilemedi.",
        )

    detect = tespit_et

    def _mekan_zincirini_dene(
        self, lat: float, lon: float
    ):
        for saglayici in self._poi_providers:
            try:
                sonuc = saglayici.find_nearest(lat, lon)
                if sonuc:
                    return sonuc, saglayici.PROVIDER_NAME
            except Exception as exc:
                logger.warning(
                    "POI sağlayıcı hatası [%s]: %s", saglayici.PROVIDER_NAME, exc
                )
        return None, None

    _try_poi_chain = _mekan_zincirini_dene

    def _ip_zincirini_dene(self, ip_address: str | None):
        for saglayici in self._ip_providers:
            try:
                sonuc = saglayici.lookup(ip_address or "")
                if sonuc:
                    return sonuc
            except Exception as exc:
                logger.warning(
                    "IP sağlayıcı hatası [%s]: %s", saglayici.PROVIDER_NAME, exc
                )
        return None

    _try_ip_chain = _ip_zincirini_dene

    def _geocoding_dene(self, lat: float, lon: float) -> dict:
        try:
            return GeocodingService.reverse_geocode(lat, lon)
        except Exception as exc:
            logger.warning("Geocoding hatası: %s", exc)
            return {"country": None, "city": None, "formatted_address": None, "source": None}

    _try_geocoding = _geocoding_dene


LocationOrchestrator = KonumOrkestratoru

_orkestrator: KonumOrkestratoru | None = None


def konum_orkestratorunu_getir() -> KonumOrkestratoru:
    global _orkestrator
    if _orkestrator is None:
        _orkestrator = KonumOrkestratoru()
    return _orkestrator


get_location_orchestrator = konum_orkestratorunu_getir
