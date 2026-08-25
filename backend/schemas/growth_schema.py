from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field


class OnayGovdesi(BaseModel):
    confirm_send: bool


class IlerlemeGovdesi(BaseModel):
    progress: int = Field(ge=0, le=100)


class DersCevapGovdesi(BaseModel):
    answer_index: int = Field(ge=0, le=10)


class AliciGovdesi(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str | None = Field(default=None, max_length=160)
    company_name: str | None = Field(default=None, max_length=255)


class KampanyaGovdesi(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    subject: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=10, max_length=10000)
    reply_to: str | None = Field(default=None, max_length=255)
    recipients: list[AliciGovdesi] = Field(min_length=1, max_length=50)


class EpostaTeslimatOlayGovdesi(BaseModel):
    provider: str = Field(min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    event_id: str = Field(min_length=1, max_length=255)
    message_id: str = Field(min_length=3, max_length=255)
    event_type: Literal["delivered", "bounced", "complained"]
    occurred_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=500)


class TalepIlaniGovdesi(BaseModel):
    product_id: str
    quantity: str | None = Field(default=None, max_length=100)
    target_country: str = Field(default="Türkiye", min_length=2, max_length=100)
    deadline: date | None = None
    platforms: list[str] = Field(min_length=1, max_length=5)
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)


class PazarAnalizGovdesi(BaseModel):
    product_id: str
    target_country: str = Field(min_length=2, max_length=100)
    year: int | None = Field(default=None, ge=1962, le=2100)


ApprovalBody = OnayGovdesi
ProgressBody = IlerlemeGovdesi
LessonAnswerBody = DersCevapGovdesi
RecipientBody = AliciGovdesi
CampaignBody = KampanyaGovdesi
EmailDeliveryEventBody = EpostaTeslimatOlayGovdesi
DemandPostBody = TalepIlaniGovdesi
TradeMarketBody = PazarAnalizGovdesi
