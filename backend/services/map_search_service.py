import os
import re
from typing import Any
import httpx

from services.country_catalog_service import CountryCatalogService


class HaritaAramaServisi:
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    HERE_URL = "https://discover.search.hereapi.com/v1/discover"

    def ara(self, product_data: dict[str, Any], country: str, limit: int = 30) -> list[dict]:
        terimler = [product_data.get("product_name", ""), *product_data.get("sub_sectors", [])]
        terimler = [re.sub(r"[^\w\s-]", " ", terim).strip() for terim in terimler if terim and terim.strip()][:5]
        if not terimler:
            return []

        ulke_bilgisi = CountryCatalogService().find(country)
        if not ulke_bilgisi:
            return []

        kod = ulke_bilgisi.code.lower()
        kalip = "|".join(re.escape(terim) for terim in terimler)
        sorgu = f'''[out:json][timeout:25];
area["ISO3166-1"="{kod.upper()}"][admin_level=2]->.country;
(nwr(area.country)["name"~"{kalip}",i];
nwr(area.country)["description"~"{kalip}",i];
nwr(area.country)["product"~"{kalip}",i];);
out center {limit};'''

        try:
            yanit = httpx.post(self.OVERPASS_URL, content=sorgu, timeout=35.0, headers={"User-Agent": "Pusula-MVP/1.0"})
            yanit.raise_for_status()
            satirlar = [self._osmden_donustur(oge, country) for oge in yanit.json().get("elements", [])]
            satirlar = [satir for satir in satirlar if satir.get("name")]
            if satirlar:
                return satirlar[:limit]
        except (httpx.HTTPError, ValueError):
            pass

        return self._here_ile_ara(terimler[0], kod, country, limit)

    search = ara

    def _here_ile_ara(self, term: str, code: str, country: str, limit: int) -> list[dict]:
        api_anahtari = os.getenv("HERE_API_KEY")
        if not api_anahtari:
            return []
        try:
            yanit = httpx.get(
                self.HERE_URL,
                params={"q": term, "in": f"countryCode:{code.upper()}", "limit": min(limit, 100), "apiKey": api_anahtari},
                timeout=20.0,
            )
            yanit.raise_for_status()
            return [{
                "name": oge.get("title"),
                "website": self._ilk_iletisim(oge, "www"),
                "phone": self._ilk_iletisim(oge, "phone"),
                "email": self._ilk_iletisim(oge, "email"),
                "address": oge.get("address", {}).get("label"),
                "country": country,
                "source": "here",
            } for oge in yanit.json().get("items", [])]
        except (httpx.HTTPError, ValueError, IndexError):
            return []

    _search_here = _here_ile_ara

    @staticmethod
    def _osmden_donustur(item: dict, country: str) -> dict:
        etiketler = item.get("tags", {})
        osm_url = f"https://www.openstreetmap.org/{item.get('type')}/{item.get('id')}"
        return {
            "name": etiketler.get("name"),
            "website": etiketler.get("website") or etiketler.get("contact:website") or osm_url,
            "phone": etiketler.get("phone") or etiketler.get("contact:phone"),
            "email": etiketler.get("email") or etiketler.get("contact:email"),
            "address": " ".join(filter(None, [etiketler.get("addr:street"), etiketler.get("addr:housenumber"), etiketler.get("addr:city")])),
            "country": country,
            "source": "overpass",
        }

    _from_osm = _osmden_donustur

    @staticmethod
    def _ilk_iletisim(item: dict, kind: str) -> str | None:
        iletisimler = item.get("contacts") or []
        degerler = iletisimler[0].get(kind) or [] if iletisimler else []
        return degerler[0].get("value") if degerler else None

    _first_contact = _ilk_iletisim


MapSearchService = HaritaAramaServisi
