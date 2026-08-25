import logging
import os
import httpx

from services.location.interfaces import IPoiProvider
from schemas.location_schema import POIResult

logger = logging.getLogger(__name__)

_HERE_TARAMA_URL = "https://browse.search.hereapi.com/v1/browse"


class HereMekanServisi(IPoiProvider):
    SAGLAYICI_ADI = "here"
    PROVIDER_NAME = SAGLAYICI_ADI

    def __init__(self, radius_m: int = 100):
        self.radius_m = radius_m
        self.api_key = os.getenv("HERE_API_KEY", "")

    def en_yakini_bul(self, lat: float, lon: float) -> POIResult | None:
        if not self.api_key:
            logger.warning("HERE_API_KEY tanımlı değil, servis devre dışı.")
            return None

        parametreler = {
            "at": f"{lat},{lon}",
            "limit": 1,
            "circle": f"{lat},{lon};r={self.radius_m}",
            "categories": "700-7600-0116,700-7600-0117,600-6900,700-7600-0000",
            "apiKey": self.api_key,
        }

        try:
            with httpx.Client(timeout=10.0) as istemci:
                yanit = istemci.get(_HERE_TARAMA_URL, params=parametreler)
                yanit.raise_for_status()
                veri = yanit.json()

            ogeler = veri.get("items", [])
            if not ogeler:
                logger.info("HERE: %s,%s yakınında POI bulunamadı.", lat, lon)
                return None

            return self._ogeyi_ayristir(ogeler[0], lat, lon)

        except httpx.HTTPStatusError as exc:
            logger.error("HERE HTTP hatası: %s — %s", exc.response.status_code, exc.response.text[:200])
        except Exception as exc:
            logger.error("HERE POI servisi hatası: %s", exc)

        return None

    find_nearest = en_yakini_bul

    def _ogeyi_ayristir(self, item: dict, origin_lat: float, origin_lon: float) -> POIResult:
        adres = item.get("address", {})
        kategoriler = item.get("categories", [])
        kategori_adi = kategoriler[0].get("name") if kategoriler else None

        iletisimler = item.get("contacts", [{}])[0]
        telefon = None
        web_sitesi = None

        for tel in iletisimler.get("phone", []):
            telefon = tel.get("value")
            break
        for web in iletisimler.get("www", []):
            web_sitesi = web.get("value")
            break

        adres_metni = ", ".join(filter(None, [
            adres.get("street"),
            adres.get("houseNumber"),
            adres.get("postalCode"),
            adres.get("city"),
            adres.get("countryName"),
        ]))

        mesafe = item.get("distance", 0)

        return POIResult(
            name=item.get("title"),
            category=kategori_adi,
            address=adres_metni or None,
            phone=telefon,
            website=web_sitesi,
            distance_m=float(mesafe),
            confidence=max(0.6, min(1.0, 1.0 - mesafe / (self.radius_m * 3))),
        )

    _parse_item = _ogeyi_ayristir


HerePoiService = HereMekanServisi
