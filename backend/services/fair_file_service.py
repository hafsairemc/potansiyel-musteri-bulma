import io
import zipfile
from pathlib import Path


class FuarDosyaHatasi(ValueError):
    pass


FairFileError = FuarDosyaHatasi


class FuarDosyaServisi:
    izin_verilen_esleme_alanlari = {
        "company_name", "website", "country", "city",
        "sector", "description", "email", "phone",
    }
    allowed_mapping_fields = izin_verilen_esleme_alanlari

    def icerigi_dogrula(self, filename: str, content: bytes) -> str:
        uzanti = Path(filename).suffix.lower()
        if uzanti not in {".xlsx", ".csv"}:
            raise FuarDosyaHatasi("Yalnız XLSX veya CSV dosyası yüklenebilir")
        if not content:
            raise FuarDosyaHatasi("Dosya boş olamaz")
        if uzanti == ".xlsx":
            self._xlsx_dogrula(content)
        else:
            self._csv_dogrula(content)
        return uzanti

    validate_content = icerigi_dogrula

    def sutunlari_dogrula(self, columns) -> list[str]:
        duzenlenmis = [str(sutun).strip() for sutun in columns]
        if not duzenlenmis or not any(duzenlenmis):
            raise FuarDosyaHatasi("Dosyada sütun başlığı bulunamadı")
        if len(duzenlenmis) > 200:
            raise FuarDosyaHatasi("Dosyada en fazla 200 sütun olabilir")
        return duzenlenmis

    validate_columns = sutunlari_dogrula

    def eslemeyi_dogrula(self, mapping: dict[str, str], source_columns: list[str]) -> dict[str, str]:
        bilinmeyen_alanlar = set(mapping) - self.izin_verilen_esleme_alanlari
        if bilinmeyen_alanlar:
            raise FuarDosyaHatasi(f"Desteklenmeyen eşleme alanı: {', '.join(sorted(bilinmeyen_alanlar))}")
        temizlenmis = {anahtar: deger.strip() for anahtar, deger in mapping.items() if isinstance(deger, str) and deger.strip()}
        if not temizlenmis.get("company_name"):
            raise FuarDosyaHatasi("Firma adı sütunu zorunludur")
        if source_columns:
            bilinmeyen_sutunlar = set(temizlenmis.values()) - set(source_columns)
            if bilinmeyen_sutunlar:
                raise FuarDosyaHatasi(f"Dosyada bulunmayan sütun: {', '.join(sorted(bilinmeyen_sutunlar))}")
        if len(temizlenmis.values()) != len(set(temizlenmis.values())):
            raise FuarDosyaHatasi("Bir dosya sütunu yalnız bir alana eşlenebilir")
        return temizlenmis

    validate_mapping = eslemeyi_dogrula

    @staticmethod
    def _xlsx_dogrula(content: bytes) -> None:
        if not content.startswith(b"PK"):
            raise FuarDosyaHatasi("Dosya geçerli bir XLSX değil")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as arsiv:
                isimler = set(arsiv.namelist())
                if "[Content_Types].xml" not in isimler or "xl/workbook.xml" not in isimler:
                    raise FuarDosyaHatasi("Dosya geçerli bir Excel çalışma kitabı değil")
                if len(isimler) > 1000:
                    raise FuarDosyaHatasi("Excel dosyası çok fazla iç öğe içeriyor")
                if sum(oge.file_size for oge in arsiv.infolist()) > 50 * 1024 * 1024:
                    raise FuarDosyaHatasi("Excel dosyasının açılmış boyutu çok büyük")
        except zipfile.BadZipFile as exc:
            raise FuarDosyaHatasi("Dosya geçerli bir XLSX değil") from exc

    _validate_xlsx = _xlsx_dogrula

    @staticmethod
    def _csv_dogrula(content: bytes) -> None:
        if b"\x00" in content:
            raise FuarDosyaHatasi("CSV dosyası ikili veri içeremez")
        for kodlama in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
            try:
                content.decode(kodlama)
                return
            except UnicodeDecodeError:
                continue
        raise FuarDosyaHatasi("CSV karakter kodlaması desteklenmiyor")

    _validate_csv = _csv_dogrula


FairFileService = FuarDosyaServisi
