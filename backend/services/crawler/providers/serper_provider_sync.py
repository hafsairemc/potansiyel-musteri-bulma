import os
import logging
import httpx

from core.interfaces import SearchQuery, SearchResult
from services.country_catalog_service import CountryCatalogService

logger = logging.getLogger(__name__)

ULKE_GL = {
    "Germany": "de", "Almanya": "de",
    "France": "fr",  "Fransa": "fr",
    "United States": "us", "US": "us", "ABD": "us",
    "Turkey": "tr",  "Türkiye": "tr",
    "United Kingdom": "gb", "İngiltere": "gb", "Birleşik Krallık": "gb",
    "Netherlands": "nl", "Hollanda": "nl",
    "Poland": "pl",  "Polonya": "pl",
    "Italy": "it",   "İtalya": "it",
    "Spain": "es",   "İspanya": "es",
    "Russia": "ru",  "Rusya": "ru",
    "China": "cn",   "Çin": "cn",
    "Japan": "jp",   "Japonya": "jp",
    "UAE": "ae",     "BAE": "ae",
    "Saudi Arabia": "sa", "Suudi Arabistan": "sa",
    "India": "in",   "Hindistan": "in",
    "Egypt": "eg",   "Mısır": "eg",
    "Georgia": "ge", "Gürcistan": "ge",
    "Azerbaijan": "az", "Azerbaycan": "az",
    "Bulgaria": "bg", "Bulgaristan": "bg",
}
COUNTRY_GL = ULKE_GL


class SerperSaglayiciSenkron:
    BASE_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY", "")

    def ara(self, query: SearchQuery, max_pages: int = 1) -> list[SearchResult]:
        if not self.api_key:
            logger.error("SERPER_API_KEY eksik!")
            return []

        sonuclar: list[SearchResult] = []
        ulke = CountryCatalogService().find(query.target_country or "")
        gl_kodu = ulke.code.lower() if ulke else ULKE_GL.get(query.target_country or "Global")

        with httpx.Client(timeout=15.0) as istemci:
            for sayfa in range(max_pages):
                istek_paketi = {"q": query.query_text, "num": 10, "page": sayfa + 1}
                if gl_kodu:
                    istek_paketi["gl"] = gl_kodu

                try:
                    yanit = istemci.post(
                        self.BASE_URL,
                        headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                        json=istek_paketi,
                    )
                    yanit.raise_for_status()
                    veri = yanit.json()
                    for sira, oge in enumerate(veri.get("organic", [])):
                        url = oge.get("link", "")
                        if url and url.startswith("http"):
                            sonuclar.append(SearchResult(
                                url=url,
                                title=oge.get("title", ""),
                                snippet=oge.get("snippet", ""),
                                position=(sayfa * 10) + sira + 1,
                                query=query.query_text,
                                platform="Google",
                            ))
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 429:
                        raise RuntimeError("SERPER_QUOTA: Serper kotası aşıldı") from exc
                    raise RuntimeError(f"SERPER_HTTP_{exc.response.status_code}: Serper isteği başarısız") from exc
                except Exception as exc:
                    logger.error("Serper hata: %s", exc)
                    raise

        logger.info("Serper: %s sonuç → '%s'", len(sonuclar), query.query_text[:50])
        return sonuclar

    search = ara


SerperProviderSync = SerperSaglayiciSenkron
