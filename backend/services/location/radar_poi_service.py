import logging
import os
import httpx

from services.location.interfaces import IPoiProvider
from schemas.location_schema import POIResult

logger = logging.getLogger(__name__)

_RADAR_ARAMA_URL = "https://api.radar.io/v1/search/places"


class RadarMekanServisi(IPoiProvider):
    SAGLAYICI_ADI = "radar"
    PROVIDER_NAME = SAGLAYICI_ADI

    def __init__(self, radius_m: int = 100):
        self.radius_m = radius_m
        self.api_key = os.getenv("RADAR_API_KEY", "")

    def en_yakini_bul(self, lat: float, lon: float) -> POIResult | None:
        if not self.api_key:
            logger.warning("RADAR_API_KEY tanımlı değil, servis devre dışı.")
            return None

        parametreler = {
            "near": f"{lat},{lon}",
            "radius": self.radius_m,
            "limit": 1,
            "categories": "office,company,store,mall,shopping_mall,shopping_center",
        }
        basliklar = {"Authorization": self.api_key}

        try:
            with httpx.Client(timeout=10.0) as istemci:
                yanit = istemci.get(_RADAR_ARAMA_URL, params=parametreler, headers=basliklar)
                yanit.raise_for_status()
                veri = yanit.json()

            mekanlar = veri.get("places", [])
            if not mekanlar:
                logger.info("Radar: %s,%s yakınında POI bulunamadı.", lat, lon)
                return None

            return self._mekani_ayristir(mekanlar[0], lat, lon)

        except httpx.HTTPStatusError as exc:
            logger.error("Radar HTTP hatası: %s — %s", exc.response.status_code, exc.response.text[:200])
        except Exception as exc:
            logger.error("Radar POI servisi hatası: %s", exc)

        return None

    find_nearest = en_yakini_bul

    def _mekani_ayristir(self, place: dict, origin_lat: float, origin_lon: float) -> POIResult:
        kategoriler = place.get("categories", [])
        kategori = kategoriler[0] if kategoriler else None

        konum = place.get("location", {})
        mekan_lat = konum.get("coordinates", [origin_lon, origin_lat])[1]
        mekan_lon = konum.get("coordinates", [origin_lon, origin_lat])[0]

        mesafe = self._haversine(origin_lat, origin_lon, mekan_lat, mekan_lon)

        return POIResult(
            name=place.get("name"),
            category=kategori,
            address=place.get("formattedAddress"),
            phone=None,
            website=None,
            distance_m=round(mesafe, 1),
            confidence=max(0.5, min(1.0, 1.0 - mesafe / (self.radius_m * 3))),
        )

    _parse_place = _mekani_ayristir

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        import math
        R = 6_371_000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))


RadarPoiService = RadarMekanServisi
