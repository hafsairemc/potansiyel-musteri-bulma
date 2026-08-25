import csv
import io
from urllib.parse import urlparse

from services.domain_input_service import DomainInputService


class FuarKaynakHatasi(ValueError):
    pass


FairSourceError = FuarKaynakHatasi


class FuarKaynakServisi:
    azami_kayit_sayisi = 1000
    max_entries = azami_kayit_sayisi

    def csv_olustur(self, source_text: str) -> tuple[bytes, int]:
        satirlar = [satir.strip() for satir in source_text.splitlines() if satir.strip()]
        if not satirlar:
            raise FuarKaynakHatasi("En az bir firma adı veya website adresi girin")
        if len(satirlar) > self.azami_kayit_sayisi:
            raise FuarKaynakHatasi(
                f"Tek seferde en fazla {self.azami_kayit_sayisi} katılımcı girilebilir"
            )

        tablo_satirlari = []
        gorulenler = set()
        for satir in satirlar:
            firma_adi, web_sitesi = self._satiri_ayristir(satir)
            anahtar = (firma_adi.casefold(), web_sitesi.casefold())
            if anahtar in gorulenler:
                continue
            gorulenler.add(anahtar)
            tablo_satirlari.append((firma_adi, web_sitesi))

        akis = io.StringIO(newline="")
        yazici = csv.writer(akis)
        yazici.writerow(["Firma Adı", "Website"])
        yazici.writerows(tablo_satirlari)
        return akis.getvalue().encode("utf-8-sig"), len(tablo_satirlari)

    build_csv = csv_olustur

    def _satiri_ayristir(self, line: str) -> tuple[str, str]:
        parcalar = [parca.strip() for parca in self._satiri_bol(line)]
        url_parcasi = next((p for p in parcalar if self._url_gibi_mi(p)), "")
        isim_parcasi = next((p for p in parcalar if p != url_parcasi), "")

        if not url_parcasi:
            isim = self._ismi_temizle(line)
            return isim, ""

        web_sitesi, alan_adi = self._web_sitesini_normallestir(url_parcasi)
        isim = (
            self._ismi_temizle(isim_parcasi)
            if isim_parcasi
            else alan_adi.split(".")[0].replace("-", " ").title()
        )
        return isim, web_sitesi

    _parse_line = _satiri_ayristir

    @staticmethod
    def _satiri_bol(line: str) -> list[str]:
        for ayrac in ("\t", "|", ";"):
            if ayrac in line:
                return line.split(ayrac, 1)
        return [line]

    _split_line = _satiri_bol

    @staticmethod
    def _url_gibi_mi(value: str) -> bool:
        aday = value.strip().lower()
        if aday.startswith(("http://", "https://", "www.")):
            return True
        ayristirilmis = urlparse(f"https://{aday}")
        return bool(ayristirilmis.hostname and "." in ayristirilmis.hostname and " " not in aday)

    _looks_like_url = _url_gibi_mi

    @staticmethod
    def _web_sitesini_normallestir(value: str) -> tuple[str, str]:
        try:
            alan_adi = DomainInputService.normalize(value)
        except ValueError as exc:
            raise FuarKaynakHatasi(f"Geçersiz website adresi: {value}") from exc
        if not alan_adi:
            raise FuarKaynakHatasi(f"Geçersiz website adresi: {value}")
        return f"https://{alan_adi}", alan_adi

    _normalize_website = _web_sitesini_normallestir

    @staticmethod
    def _ismi_temizle(value: str) -> str:
        isim = " ".join(value.split()).strip(" ,;|\t")
        if len(isim) < 2:
            raise FuarKaynakHatasi("Firma adı en az iki karakter olmalıdır")
        if len(isim) > 255:
            raise FuarKaynakHatasi("Firma adı en fazla 255 karakter olabilir")
        return isim

    _clean_name = _ismi_temizle


FairSourceService = FuarKaynakServisi
