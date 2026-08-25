import logging
import urllib.request
import urllib.parse
import json

from services.location.interfaces import IPoiProvider
from schemas.location_schema import POIResult

logger = logging.getLogger(__name__)

_ETIKET_KATEGORI_HARITASI = {
    "office":     "office",
    "shop":       "shop",
    "amenity":    "amenity",
    "company":    "company",
    "building":   "building",
    "industrial": "industrial",
}
_TAG_CATEGORY_MAP = _ETIKET_KATEGORI_HARITASI

_OVERPASS_URLLERI = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
_OVERPASS_URLS = _OVERPASS_URLLERI


class OverpassMekanServisi(IPoiProvider):
    SAGLAYICI_ADI = "overpass"
    PROVIDER_NAME = SAGLAYICI_ADI

    def __init__(self, radius_m: int = 50):
        self.radius_m = radius_m

    def en_yakini_bul(self, lat: float, lon: float) -> POIResult | None:
        sorgu = self._sorgu_olustur(lat, lon)

        for ucbirim in _OVERPASS_URLLERI:
            try:
                url = ucbirim + "?data=" + urllib.parse.quote(sorgu)
                istek = urllib.request.Request(
                    url,
                    headers={"User-Agent": "PusulaApp/2.0 (location detection)"},
                )
                with urllib.request.urlopen(istek, timeout=10) as cevap:
                    veri = json.loads(cevap.read())

                elemanlar = veri.get("elements", [])
                if elemanlar:
                    return self._ogeyi_ayristir(elemanlar[0], lat, lon)

            except Exception as exc:
                logger.warning("Overpass (%s) hatası: %s", ucbirim, exc)
                continue

        logger.info("Overpass: %s,%s civarında POI bulunamadı.", lat, lon)
        return None

    find_nearest = en_yakini_bul

    def _sorgu_olustur(self, lat: float, lon: float) -> str:
        r = self.radius_m
        return f"""
[out:json][timeout:10];
(
  node["office"](around:{r},{lat},{lon});
  node["shop"](around:{r},{lat},{lon});
  node["amenity"~"^(restaurant|cafe|bank|hospital|school|university|hotel)$"](around:{r},{lat},{lon});
  node["company"](around:{r},{lat},{lon});
  way["office"](around:{r},{lat},{lon});
  way["shop"](around:{r},{lat},{lon});
  way["building"~"^(commercial|office|retail|industrial)$"](around:{r},{lat},{lon});
);
out tags center 1;
""".strip()

    _build_query = _sorgu_olustur

    def _ogeyi_ayristir(self, el: dict, origin_lat: float, origin_lon: float) -> POIResult:
        etiketler = el.get("tags", {})

        el_lat = el.get("lat") or (el.get("center") or {}).get("lat") or origin_lat
        el_lon = el.get("lon") or (el.get("center") or {}).get("lon") or origin_lon

        mesafe = self._haversine(origin_lat, origin_lon, el_lat, el_lon)

        kategori = None
        for etiket_anahtari in _ETIKET_KATEGORI_HARITASI:
            if etiket_anahtari in etiketler:
                kategori = f"{_ETIKET_KATEGORI_HARITASI[etiket_anahtari]}:{etiketler[etiket_anahtari]}"
                break

        adres_parcalari = [
            etiketler.get("addr:street"),
            etiketler.get("addr:housenumber"),
            etiketler.get("addr:postcode"),
            etiketler.get("addr:city"),
            etiketler.get("addr:country"),
        ]
        adres = ", ".join(p for p in adres_parcalari if p) or etiketler.get("addr:full") or None

        return POIResult(
            name=etiketler.get("name") or etiketler.get("brand") or etiketler.get("operator"),
            category=kategori,
            address=adres,
            phone=etiketler.get("phone") or etiketler.get("contact:phone"),
            website=etiketler.get("website") or etiketler.get("contact:website"),
            distance_m=round(mesafe, 1),
            confidence=max(0.5, min(1.0, 1.0 - mesafe / (self.radius_m * 2))),
        )

    _parse_element = _ogeyi_ayristir

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        import math
        R = 6_371_000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))


OverpassPoiService = OverpassMekanServisi
