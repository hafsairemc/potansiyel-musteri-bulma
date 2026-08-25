import os
from collections.abc import Sequence


class AramaKaynakServisi:
    etiketler = {
        "google_web": "Google Web",
        "yandex_web": "Yandex Web",
        "google_maps": "Google Haritalar",
        "b2b_platform": "B2B Platformları",
    }
    labels = etiketler

    def __init__(self, environ=None):
        self.environ = os.environ if environ is None else environ

    def kaynak_durumu(self, source: str) -> tuple[bool, str]:
        if source == "yandex_web":
            hazir = self._var_mi("YANDEX_SEARCH_API_KEY", "YANDEX_FOLDER_ID")
            return hazir, "Yandex anahtarı ve Folder ID gerekli"
        if source in {"google_web", "b2b_platform"}:
            hazir = self._var_mi("SERPER_API_KEY")
            return hazir, "Serper API anahtarı gerekli"
        if source == "google_maps":
            return True, "Serper yoksa OpenStreetMap/Overpass kullanılacak"
        return False, "Desteklenmeyen arama kaynağı"

    status = kaynak_durumu

    def kullanilamayanlar(self, sources: Sequence[str]) -> dict[str, str]:
        sonuc = {}
        for kaynak in sources:
            hazir, mesaj = self.kaynak_durumu(kaynak)
            if not hazir:
                sonuc[kaynak] = mesaj
        return sonuc

    unavailable = kullanilamayanlar

    def _var_mi(self, *names: str) -> bool:
        return all(bool(self.environ.get(isim, "").strip()) for isim in names)

    _has = _var_mi


SearchSourceService = AramaKaynakServisi
