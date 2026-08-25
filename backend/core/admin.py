import os
from fastapi import Depends, HTTPException

from core.security import get_current_user
from services.db import admin_supabase


def yonetici_kontrolu(kullanici: dict = Depends(get_current_user)) -> dict:
    eposta = (kullanici.get("email") or kullanici.get("username") or "").strip().lower()

    izinli_epostalar = {
        adres.strip().lower()
        for adres in os.getenv("ADMIN_EMAILS", "").split(",")
        if adres.strip()
    }

    if eposta and eposta in izinli_epostalar:
        return kullanici

    if admin_supabase:
        kullanici_id = kullanici.get("id") or kullanici.get("sub")
        if kullanici_id:
            sonuc = (
                admin_supabase.table("profiles")
                .select("role,is_active")
                .eq("id", kullanici_id)
                .limit(1)
                .execute()
            )
            if sonuc.data:
                profil = sonuc.data[0]
                if profil.get("role") == "admin" and profil.get("is_active", True):
                    return kullanici

    raise HTTPException(status_code=403, detail="Yönetici yetkisi gerekli")


require_admin = yonetici_kontrolu
