from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class LocationRequest(BaseModel):
    permission: bool
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    city: str | None = None
    ip: str | None = None


class SearchJobCreate(BaseModel):
    product_id: str | None = None
    search_query: str
    target_country: str | None = None
    search_engine: str | None = "Google"


class SearchJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None = None
    product_id: str | None = None
    search_query: str
    target_country: str | None = None
    search_engine: str
    status: JobStatus
    report_url: str | None = None


GorevDurumu = JobStatus
GirisIstegi = LoginRequest
YenilemeIstegi = RefreshRequest
KonumIstegi = LocationRequest
AramaGoreviOlustur = SearchJobCreate
AramaGoreviYaniti = SearchJobResponse
