import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UrunResimSemasi(BaseModel):
    url: str


class UrunRakipSemasi(BaseModel):
    brand_name: str


class UrunSektorSemasi(BaseModel):
    industry_name: str


class HedefUlkeOlustur(BaseModel):
    country_name: str = Field(min_length=2, max_length=255)
    domain_extension: str | None = Field(
        default=None, min_length=3, max_length=20, pattern=r"^\.[a-z.]+$"
    )


class HedefUlkeYaniti(BaseModel):
    id: str
    country_name: str
    domain_extension: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TemelUrun(BaseModel):
    oem: str | None = Field(None, min_length=2, max_length=100, title="OEM Numarası")
    hs_code: str | None = Field(None, min_length=2, max_length=50, title="HS Code")

    name_tr: str = Field(..., title="Türkçe İsim", min_length=2, max_length=255)
    name_en: str | None = Field(None, title="İngilizce İsim", min_length=2, max_length=255)
    name_de: str | None = Field(None, max_length=255)
    name_fr: str | None = Field(None, max_length=255)
    name_ru: str | None = Field(None, max_length=255)
    name_es: str | None = Field(None, max_length=255)
    name_ar: str | None = Field(None, max_length=255)

    @field_validator("hs_code")
    @classmethod
    def gtip_dogrula(cls, deger: str | None) -> str | None:
        if deger is None:
            return None
        rakamlar = "".join(karakter for karakter in deger if karakter.isdigit())
        if len(rakamlar) not in {2, 4, 6, 8, 10, 12}:
            raise ValueError("GTİP 2, 4, 6, 8, 10 veya 12 haneli olmalıdır")
        return rakamlar


class UrunOlustur(TemelUrun):
    description: str | None = Field(default=None, max_length=5000)
    search_profile: dict[str, Any] = Field(default_factory=dict)
    images: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Görseller ayrı yükleme endpoint'iyle kaydedilir",
    )
    competitors: list[str] = Field(
        default_factory=list, max_length=50, description="Rakip markalar"
    )
    industries: list[str] = Field(
        default_factory=list, max_length=25, description="Bağlı sektörler"
    )
    target_countries: list[HedefUlkeOlustur] = Field(
        default_factory=list,
        max_length=25,
        description="Hedef ülkeler ve domain uzantıları",
    )
    target_languages: list[str] = Field(
        default_factory=lambda: ["İngilizce"], max_length=10
    )

    @field_validator("images")
    @classmethod
    def resim_yukleme_kontrolu(cls, deger: list[str]) -> list[str]:
        if deger:
            raise ValueError("Görseller ürün oluşturulduktan sonra dosya olarak yüklenmelidir")
        return deger


class UrunYaniti(TemelUrun):
    id: uuid.UUID
    user_id: str
    description: str | None = None
    search_profile: dict[str, Any] = Field(default_factory=dict)
    target_languages: list[str] = Field(default_factory=list)
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
    images: list[UrunResimSemasi] = Field(default_factory=list)
    competitors: list[UrunRakipSemasi] = Field(default_factory=list)
    industries: list[UrunSektorSemasi] = Field(default_factory=list)
    target_countries: list[HedefUlkeYaniti] = Field(default_factory=list)


ProductImageSchema = UrunResimSemasi
ProductCompetitorSchema = UrunRakipSemasi
ProductIndustrySchema = UrunSektorSemasi
TargetCountryCreate = HedefUlkeOlustur
TargetCountryResponse = HedefUlkeYaniti
ProductBase = TemelUrun
ProductCreate = UrunOlustur
ProductResponse = UrunYaniti
