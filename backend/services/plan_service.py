import os
from fastapi import HTTPException
from services.db import admin_supabase

PLANLAR = {
    "starter": {
        "name": "Başlangıç",
        "price_label": "Ücretsiz demo",
        "monthly_searches": 30,
        "countries_per_search": 3,
        "modules": ["customer_search", "assistant", "rfq", "fair", "learning", "email_campaigns", "demand_posts", "trade_data"],
    },
    "pro": {
        "name": "Profesyonel",
        "price_label": "Teklif alın",
        "monthly_searches": 300,
        "countries_per_search": 10,
        "modules": ["customer_search", "assistant", "rfq", "fair", "learning", "email_campaigns", "demand_posts", "trade_data"],
    },
    "enterprise": {
        "name": "Kurumsal",
        "price_label": "Özel teklif",
        "monthly_searches": None,
        "countries_per_search": 25,
        "modules": ["customer_search", "assistant", "rfq", "fair", "learning", "email_campaigns", "demand_posts", "trade_data"],
    },
}

PLANS = PLANLAR


class PlanServisi:
    @staticmethod
    def katalog() -> list[dict]:
        return [{"key": anahtar, **deger} for anahtar, deger in PLANLAR.items()]

    catalog = katalog

    def plani_getir(self, user_id: str) -> str:
        if not admin_supabase:
            return "starter"
        sonuc = admin_supabase.table("profiles").select("plan,is_active").eq("id", user_id).limit(1).execute()
        profil = sonuc.data[0] if sonuc.data else {}
        if profil and not profil.get("is_active", True):
            raise HTTPException(status_code=403, detail="Kullanıcı hesabı devre dışı")
        plan = profil.get("plan") or "starter"
        return plan if plan in PLANLAR else "starter"

    get_plan = plani_getir

    def yetkileri_getir(self, user_id: str) -> dict:
        plan = self.plani_getir(user_id)
        return {"plan": plan, **PLANLAR[plan], "enforced": self.limitler_zorunlu_mu()}

    entitlements = yetkileri_getir

    @staticmethod
    def plani_dogrula(plan: str) -> str:
        if plan not in PLANLAR:
            raise HTTPException(status_code=422, detail="Geçersiz plan")
        return plan

    validate_plan = plani_dogrula

    def modul_iznini_denetle(self, user_id: str, module: str) -> None:
        if not self.limitler_zorunlu_mu():
            return
        haklar = self.yetkileri_getir(user_id)
        if module not in haklar["modules"]:
            raise HTTPException(status_code=403, detail="Bu modül mevcut planınıza dahil değil")

    ensure_module = modul_iznini_denetle

    @staticmethod
    def limitler_zorunlu_mu() -> bool:
        return os.getenv("ENFORCE_PLAN_LIMITS", "false").lower() in {"1", "true", "yes"}

    is_enforced = limitler_zorunlu_mu


PlanService = PlanServisi
