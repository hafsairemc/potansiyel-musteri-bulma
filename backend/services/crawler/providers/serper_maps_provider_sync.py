import os
from urllib.parse import quote_plus
import httpx

from core.interfaces import SearchResult
from services.country_catalog_service import CountryCatalogService


class SerperHaritalarHatasi(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


SerperMapsError = SerperHaritalarHatasi


class SerperHaritalarSaglayiciSenkron:
    URL = "https://google.serper.dev/maps"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY", "")

    def ara(self, product_name: str, country: str = "Türkiye") -> list[SearchResult]:
        if not self.api_key:
            raise SerperHaritalarHatasi("SERPER_NOT_CONFIGURED", "SERPER_API_KEY eksik")

        ulke_bilgisi = CountryCatalogService().find(country)
        yapilandirilan_sehirler = os.getenv("MAP_SEARCH_CITIES", "") if country == "Türkiye" else ""
        sehirler = [oge.strip() for oge in yapilandirilan_sehirler.split(",") if oge.strip()]
        if not sehirler:
            sehirler = list(ulke_bilgisi.cities) if ulke_bilgisi else [country]

        ulke_kodu = ulke_bilgisi.code.lower() if ulke_bilgisi else "tr"
        dil_kodu = {
            "Türkçe": "tr", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es",
            "Rusça": "ru", "Arapça": "ar", "Çince": "zh-cn", "Japonca": "ja",
        }.get(ulke_bilgisi.languages[0] if ulke_bilgisi else "Türkçe", "en")

        butce = max(1, min(int(os.getenv("MAPS_MAX_CITY_QUERIES", "3")), len(sehirler)))
        satirlar: list[SearchResult] = []

        with httpx.Client(timeout=10.0) as istemci:
            for sehir in sehirler[:butce]:
                sorgu = f"{product_name} toptancı distribütör tedarikçi {sehir}"
                yanit = istemci.post(
                    self.URL,
                    headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                    json={"q": sorgu, "gl": ulke_kodu, "hl": dil_kodu, "location": f"{sehir}, {country}"},
                )
                if yanit.status_code == 429:
                    raise SerperHaritalarHatasi("SERPER_QUOTA", "Serper Maps kotası aşıldı")
                try:
                    yanit.raise_for_status()
                    veri = yanit.json()
                except (httpx.HTTPError, ValueError) as exc:
                    raise SerperHaritalarHatasi("SERPER_MAPS_ERROR", f"Serper Maps yanıtı işlenemedi: {exc}") from exc

                for oge in veri.get("places", []):
                    baslik = oge.get("title") or oge.get("name") or "Bilinmiyor"
                    harita_url = oge.get("link") or ""
                    if "google." not in harita_url or "/maps" not in harita_url:
                        konum_metni = " ".join(filter(None, [baslik, oge.get("address"), sehir]))
                        harita_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(konum_metni)}"

                    satirlar.append(SearchResult(
                        url=harita_url,
                        title=baslik,
                        snippet=oge.get("category", ""),
                        position=len(satirlar) + 1,
                        query=sorgu,
                        platform="Google Maps",
                        address=oge.get("address"),
                        phone=oge.get("phoneNumber") or oge.get("phone"),
                        country=country,
                        city=sehir,
                    ))

        return satirlar

    search = ara


SerperMapsProviderSync = SerperHaritalarSaglayiciSenkron
