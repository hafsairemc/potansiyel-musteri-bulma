from typing import Literal
from pydantic import BaseModel, Field

AramaKaynagi = Literal["google_web", "yandex_web", "google_maps", "b2b_platform"]
SearchSource = AramaKaynagi


def varsayilan_arama_kaynaklari() -> list[AramaKaynagi]:
    return ["google_web", "yandex_web", "google_maps", "b2b_platform"]


default_search_sources = varsayilan_arama_kaynaklari


class AramaGrubuOlustur(BaseModel):
    product_id: str
    target_countries: list[str] = Field(min_length=1, max_length=25)
    sources: list[AramaKaynagi] = Field(
        default_factory=varsayilan_arama_kaynaklari,
        min_length=1,
        max_length=4,
    )


class AramaGrubuOlusturuldu(BaseModel):
    id: str
    status: str
    total_jobs: int
    job_ids: list[str]


class GrupDurumYaniti(BaseModel):
    id: str
    status: str
    progress: int
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    jobs: list[dict]


class SonucSayfasi(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int
    stats: dict
    results: list[dict]


class DisaAktarmaOlusturuldu(BaseModel):
    id: str
    status: str


class DisaAktarmaIstegi(BaseModel):
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    source: AramaKaynagi | None = None
    platform: str | None = Field(default=None, max_length=100)
    customer_type: str | None = Field(default=None, max_length=50)
    sector_match: Literal["main", "sub"] | None = None
    min_score: int = Field(default=0, ge=0, le=100)
    min_relevance: int = Field(default=45, ge=0, le=100)
    q: str | None = Field(default=None, max_length=100)


class DisaAktarmaDurumu(BaseModel):
    id: str
    status: str
    download_url: str | None = None
    error_message: str | None = None


SearchBatchCreate = AramaGrubuOlustur
SearchBatchCreated = AramaGrubuOlusturuldu
BatchStatusResponse = GrupDurumYaniti
ResultsPage = SonucSayfasi
ExportCreated = DisaAktarmaOlusturuldu
ExportRequest = DisaAktarmaIstegi
ExportStatus = DisaAktarmaDurumu
