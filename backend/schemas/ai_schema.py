from pydantic import BaseModel, Field


class CeviriIstegi(BaseModel):
    product_name: str = Field(..., title="Ürün Adı", description="Kullanıcıdan gelen aranacak ürün adı veya terim")


class CeviriYaniti(BaseModel):
    original_input: str = Field(..., title="Orijinal Girdi")
    validated_technical_term_en: str = Field(..., title="Önerilen İngilizce Teknik Terim")
    translations: dict[str, str] = Field(..., title="Önerilen Çeviriler")
    verification_status: str = "ai_suggested"
    evidence: list[dict[str, str]] = Field(default_factory=list)


TranslationRequest = CeviriIstegi
TranslationResponse = CeviriYaniti
