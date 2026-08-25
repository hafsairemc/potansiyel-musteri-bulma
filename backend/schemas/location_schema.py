from typing import Literal
from pydantic import BaseModel, Field


class MekanSonucu(BaseModel):
    name: str | None = Field(None, description="İşletme / Kurum adı")
    category: str | None = Field(None, description="Yer türü (office, shop, restaurant...)")
    address: str | None = Field(None, description="Tam adres")
    phone: str | None = Field(None, description="Telefon numarası")
    website: str | None = Field(None, description="Web sitesi")
    distance_m: float | None = Field(None, description="Merkeze mesafe (metre)")
    confidence: float | None = Field(
        None, ge=0.0, le=1.0,
        description="Tespit güven skoru (0-1)"
    )


class IPSonucu(BaseModel):
    ip: str | None = Field(None, description="Tespit edilen IP adresi")
    org: str | None = Field(None, description="Organizasyon / ISP adı (kurumsal ağ tespiti)")
    isp: str | None = Field(None, description="İnternet servis sağlayıcısı")
    is_corporate: bool = Field(False, description="Kurumsal ağ olduğu tahmin ediliyor mu?")
    country: str | None = None
    city: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class KonumTespitSonucu(BaseModel):
    id: str | None = Field(None, description="Veritabanı ziyaretçi kayıt ID'si")
    detection_method: Literal["gps_poi", "ip_fallback", "none"] = Field(
        "none",
        description="Hangi yöntem kullanıldı?"
    )
    gps_available: bool = Field(False, description="GPS koordinatı alınabildi mi?")
    permission_granted: bool = Field(False, description="Kullanıcı konum izni verdi mi?")

    poi: MekanSonucu | None = None
    ip_data: IPSonucu | None = None

    country: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    formatted_address: str | None = Field(
        None,
        description="Geocoding'den dönen tam adres (cadde, ilçe, şehir, ülke)"
    )
    provider: str | None = Field(
        None,
        description="Aktif POI sağlayıcısı: 'overpass', 'here', 'radar', 'nominatim', 'google'"
    )
    error: str | None = Field(None, description="Varsa hata mesajı")


POIResult = MekanSonucu
IPResult = IPSonucu
LocationDetectionResult = KonumTespitSonucu
