import os
import json
import logging
import urllib.request
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

_onbellek: dict = {}
_cache = _onbellek
_HASSASIYET = 4


def _onbellek_anahtari(lat: float, lon: float) -> tuple:
    return (round(lat, _HASSASIYET), round(lon, _HASSASIYET))


_cache_key = _onbellek_anahtari


def _bos_sonuc() -> dict:
    return {"country": None, "city": None, "formatted_address": None, "source": "google"}


_empty = _bos_sonuc


class CografiKonumServisi:
    @staticmethod
    def ters_cografi_kodla(lat: float, lon: float) -> dict:
        anahtar = _onbellek_anahtari(lat, lon)
        if anahtar in _onbellek:
            logger.debug("Geocoding önbellekten getirildi: %s", anahtar)
            return _onbellek[anahtar]

        sonuc = CografiKonumServisi._google_cografi_kodlama_cagir(lat, lon)
        _onbellek[anahtar] = sonuc
        return sonuc

    reverse_geocode = ters_cografi_kodla

    @staticmethod
    def sehir_ve_ulke_getir(lat: float, lon: float) -> dict:
        return CografiKonumServisi.ters_cografi_kodla(lat, lon)

    get_city_and_country = sehir_ve_ulke_getir

    @staticmethod
    def _google_cografi_kodlama_cagir(lat: float, lon: float) -> dict:
        api_anahtari = os.getenv("GOOGLE_GEOCODING_API_KEY", "")
        if not api_anahtari:
            logger.info("Google Geocoding API anahtarı tanımlı değil")
            return _bos_sonuc()

        parametreler = {
            "latlng": f"{lat},{lon}",
            "key": api_anahtari,
            "language": "tr",
        }
        url = "https://maps.googleapis.com/maps/api/geocode/json?" + urlencode(parametreler)

        try:
            istek = urllib.request.Request(url, headers={"User-Agent": "PusulaApp/2.0"})
            with urllib.request.urlopen(istek, timeout=10) as cevap:
                veri = json.loads(cevap.read())

            durum = veri.get("status")
            if durum != "OK":
                hata_mesaji = veri.get("error_message", "Detay belirtilmedi.")
                logger.warning("Google Geocoding başarısız: %s - %s", durum, hata_mesaji)
                return _bos_sonuc()

            sonuclar = veri.get("results", [])
            if not sonuclar:
                logger.info("Google Geocoding sonucu bulunamadı")
                return _bos_sonuc()

            en_iyi = sonuclar[0]
            bicimlendirilmis_adres = en_iyi.get("formatted_address")
            ulke = None
            sehir = None

            for bilesen in en_iyi.get("address_components", []):
                turler = bilesen.get("types", [])
                if "country" in turler:
                    ulke = bilesen.get("long_name")
                if "locality" in turler or "administrative_area_level_1" in turler:
                    if not sehir:
                        sehir = bilesen.get("long_name")

            logger.info("Google Geocoding başarılı: %s", bicimlendirilmis_adres)
            return {
                "country": ulke,
                "city": sehir,
                "formatted_address": bicimlendirilmis_adres,
                "source": "google",
            }
        except Exception as exc:
            logger.error("Google Geocoding bağlantı hatası: %s", exc)
            return _bos_sonuc()

    _call_google_geocoding = _google_cografi_kodlama_cagir


GeocodingService = CografiKonumServisi
