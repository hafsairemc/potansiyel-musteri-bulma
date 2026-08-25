import os
from services.country_catalog_service import CountryCatalogService
from services.plan_service import PlanService


class AramaKapsamiHatasi(ValueError):
    pass


SearchScopeError = AramaKapsamiHatasi


class AramaKapsamServisi:
    hard_limit = 25

    def __init__(self):
        yapilandirilan = int(os.getenv("MAX_COUNTRIES_PER_BATCH", "10"))
        self.default_limit = max(1, min(yapilandirilan, self.hard_limit))
        self.catalog = CountryCatalogService()

    def ulkeleri_dogrula(self, values: list[str], user_id: str) -> list[str]:
        benzersiz = []
        bilinmeyenler = []
        for deger in values:
            ulke = self.catalog.find(deger)
            if not ulke:
                bilinmeyenler.append(deger.strip())
                continue
            if ulke.name not in benzersiz:
                benzersiz.append(ulke.name)

        if bilinmeyenler:
            raise AramaKapsamiHatasi(f"Ülke kataloğunda bulunamadı: {', '.join(bilinmeyenler[:3])}")

        limit = self._limit_getir(user_id)
        if len(benzersiz) > limit:
            raise AramaKapsamiHatasi(f"Bir aramada en fazla {limit} ülke seçebilirsiniz")

        return benzersiz

    countries = ulkeleri_dogrula

    def _limit_getir(self, user_id: str) -> int:
        plan_servisi = PlanService()
        if not plan_servisi.is_enforced():
            return self.default_limit
        haklar = plan_servisi.entitlements(user_id)
        return min(int(haklar["countries_per_search"]), self.hard_limit)

    _limit = _limit_getir


SearchScopeService = AramaKapsamServisi
