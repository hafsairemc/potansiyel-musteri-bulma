import base64
import logging
import os
import xml.etree.ElementTree as ET
import httpx

from core.interfaces import SearchQuery, SearchResult
from services.country_catalog_service import CountryCatalogService

logger = logging.getLogger(__name__)


class YandexSaglayiciHatasi(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


YandexProviderError = YandexSaglayiciHatasi


class YandexSaglayiciSenkron:
    URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"

    def __init__(self):
        self.api_key = os.getenv("YANDEX_SEARCH_API_KEY", "")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID", "")

    def ara(self, query: SearchQuery, max_pages: int = 1) -> list[SearchResult]:
        if not self.api_key or not self.folder_id:
            raise YandexSaglayiciHatasi("YANDEX_NOT_CONFIGURED", "Yandex Search API anahtarı veya folder ID eksik")

        sonuclar: list[SearchResult] = []
        ulke = CountryCatalogService().find(query.target_country or "")
        arama_tipi = {"TR": "SEARCH_TYPE_TR", "RU": "SEARCH_TYPE_RU"}.get(
            ulke.code if ulke else "",
            "SEARCH_TYPE_COM",
        )
        basliklar = {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=25.0) as istemci:
            for sayfa in range(max(1, min(max_pages, 3))):
                istek_paketi = {
                    "query": {
                        "searchType": arama_tipi,
                        "queryText": query.query_text,
                        "familyMode": "FAMILY_MODE_MODERATE",
                        "page": sayfa,
                    },
                    "sortSpec": {"sortMode": "SORT_MODE_BY_RELEVANCE"},
                    "groupSpec": {"groupMode": "GROUP_MODE_DEEP", "groupsOnPage": 10, "docsInGroup": 1},
                    "maxPassages": 2,
                }
                try:
                    yanit = istemci.post(self.URL, headers=basliklar, json=istek_paketi)
                    if yanit.status_code == 429:
                        raise YandexSaglayiciHatasi("YANDEX_QUOTA", "Yandex Search API kotası aşıldı")
                    if yanit.status_code in {401, 403}:
                        raise YandexSaglayiciHatasi("YANDEX_AUTH", "Yandex Search API kimlik bilgileri reddedildi")
                    yanit.raise_for_status()
                    sayfa_sonuclari = self._yaniti_ayristir(yanit.json(), query.query_text, sayfa)
                    sonuclar.extend(sayfa_sonuclari)
                    if not sayfa_sonuclari:
                        break
                except YandexSaglayiciHatasi:
                    raise
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    raise YandexSaglayiciHatasi("YANDEX_TIMEOUT", "Yandex Search API zaman aşımına uğradı") from exc
                except (httpx.HTTPError, ValueError, ET.ParseError) as exc:
                    raise YandexSaglayiciHatasi("YANDEX_BAD_RESPONSE", f"Yandex Search API yanıtı işlenemedi: {exc}") from exc

        return sonuclar

    search = ara

    @staticmethod
    def _yaniti_ayristir(data: dict, query_text: str, page: int) -> list[SearchResult]:
        if isinstance(data.get("webPages"), list):
            return [
                SearchResult(
                    url=oge.get("url", ""),
                    title=oge.get("title", ""),
                    snippet=oge.get("snippet", ""),
                    position=page * 10 + indeks + 1,
                    query=query_text,
                    platform="Yandex",
                )
                for indeks, oge in enumerate(data["webPages"])
                if oge.get("url", "").startswith("http")
            ]

        ham_veri = data.get("rawData") or ""
        if not ham_veri:
            return []
        xml_metni = base64.b64decode(ham_veri).decode("utf-8", errors="replace")
        kok = ET.fromstring(xml_metni)
        satirlar: list[SearchResult] = []
        for indeks, dokuman in enumerate(kok.findall(".//doc")):
            url = (dokuman.findtext("url") or "").strip()
            if not url.startswith("http"):
                continue
            baslik_dugumu = dokuman.find("title")
            baslik = "".join(baslik_dugumu.itertext()) if baslik_dugumu is not None else ""
            paragraflar = ["".join(dugum.itertext()) for dugum in dokuman.findall(".//passage")]
            satirlar.append(SearchResult(
                url=url,
                title=baslik.strip(),
                snippet=" ".join(paragraflar).strip(),
                position=page * 10 + indeks + 1,
                query=query_text,
                platform="Yandex",
            ))
        return satirlar

    _parse_response = _yaniti_ayristir


YandexProviderSync = YandexSaglayiciSenkron
