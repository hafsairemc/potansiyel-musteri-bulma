from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchQuery:
    query_text: str
    target_country: str | None = None
    search_engine: str = "Google"
    query_type: str = "WEB"
    language: str | None = None


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str = ""
    snippet: str = ""
    position: int | None = None
    query: str = ""
    platform: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    country: str | None = None
    city: str | None = None


class ISearchEngineProvider(ABC):
    @abstractmethod
    async def search(self, query: SearchQuery, max_pages: int = 1) -> list[SearchResult]:
        raise NotImplementedError


AramaSorgusu = SearchQuery
AramaSonucu = SearchResult
IAramaMotoruSaglayici = ISearchEngineProvider
