import os
import logging
import httpx

from core.interfaces import ISearchEngineProvider, SearchQuery, SearchResult
from services.country_catalog_service import CountryCatalogService

logger = logging.getLogger(__name__)

ULKE_GL = {
    "Germany": "de", "Almanya": "de",
    "France": "fr", "Fransa": "fr",
    "United States": "us", "US": "us", "ABD": "us",
    "Turkey": "tr", "Türkiye": "tr",
    "United Kingdom": "gb", "İngiltere": "gb", "Birleşik Krallık": "gb",
    "Netherlands": "nl", "Hollanda": "nl",
    "Poland": "pl", "Polonya": "pl",
    "Italy": "it", "İtalya": "it",
    "Spain": "es", "İspanya": "es",
    "Russia": "ru", "Rusya": "ru",
    "China": "cn", "Çin": "cn",
    "Japan": "jp", "Japonya": "jp",
    "Brazil": "br", "Brezilya": "br",
    "UAE": "ae", "BAE": "ae",
    "Saudi Arabia": "sa", "Suudi Arabistan": "sa",
    "India": "in", "Hindistan": "in",
    "Egypt": "eg", "Mısır": "eg",
    "Georgia": "ge", "Gürcistan": "ge",
    "Azerbaijan": "az", "Azerbaycan": "az",
    "Bulgaria": "bg", "Bulgaristan": "bg",
    "Global": None,
}
COUNTRY_GL = ULKE_GL


class SerperSaglayici(ISearchEngineProvider):
    BASE_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY", "")

    async def ara(self, query: SearchQuery, max_pages: int = 1) -> list[SearchResult]:
        if not self.api_key:
            logger.error(
                "Serper API Key eksik! "
                ".env dosyasına SERPER_API_KEY ekleyin."
            )
            return []

        sonuclar: list[SearchResult] = []
        ulke = CountryCatalogService().find(query.target_country or "")
        gl_parametresi = ulke.code.lower() if ulke else ULKE_GL.get(query.target_country or "Global")

        async with httpx.AsyncClient(timeout=15.0) as istemci:
            for sayfa_no in range(max_pages):
                istek_paketi = {
                    "q": query.query_text,
                    "num": 10,
                    "page": sayfa_no + 1,
                }

                if gl_parametresi:
                    istek_paketi["gl"] = gl_parametresi

                if query.language:
                    dil_kodu = query.language[:2].lower()
                    istek_paketi["hl"] = dil_kodu

                try:
                    yanit = await istemci.post(
                        self.BASE_URL,
                        headers={
                            "X-API-KEY": self.api_key,
                            "Content-Type": "application/json",
                        },
                        json=istek_paketi,
                    )
                    yanit.raise_for_status()
                    veri = yanit.json()

                    organik = veri.get("organic", [])
                    if not organik:
                        logger.info("Sayfa %s için sonuç yok.", sayfa_no + 1)
                        break

                    for sira, oge in enumerate(organik):
                        url = oge.get("link", "")
                        baslik = oge.get("title", "")
                        ozet = oge.get("snippet", "")

                        if url and url.startswith("http"):
                            sonuclar.append(SearchResult(
                                url=url,
                                title=baslik,
                                snippet=ozet,
                                position=(sayfa_no * 10) + sira + 1,
                            ))

                    logger.info(
                        "Serper → Sorgu: '%s' | Sayfa %s | %s sonuç",
                        query.query_text[:50], sayfa_no + 1, len(organik)
                    )

                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 401:
                        logger.error("Serper API Key geçersiz veya eksik.")
                    elif exc.response.status_code == 429:
                        logger.error("Serper aylık kota aşıldı.")
                    else:
                        logger.error("Serper HTTP hatası %s: %s", exc.response.status_code, exc.response.text)
                    break
                except Exception as exc:
                    logger.error("Serper beklenmeyen hata: %s", exc)
                    break

        logger.info("Serper toplam %s sonuç döndürdü.", len(sonuclar))
        return sonuclar

    search = ara


SerperProvider = SerperSaglayici
