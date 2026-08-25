import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from core.config import settings
from core.rate_limit import limiter
from core.security import get_current_user
from models.schemas import LoginRequest, RefreshRequest
from services.auth import create_access_token
from services.db import admin_supabase, public_supabase

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/config")
@limiter.limit("30/minute")
def kimlik_ayarlari(request: Request):
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase Auth yapılandırılmamış.")
    return {
        "supabase_url": settings.supabase_url,
        "supabase_publishable_key": settings.supabase_publishable_key,
    }


@router.get("/me")
@limiter.limit("60/minute")
def profil_bilgim(request: Request, response: Response, current_user: dict = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    kullanici_id = str(current_user["sub"])
    eposta = current_user.get("email") or current_user.get("username") or ""
    profil = {}

    if admin_supabase:
        try:
            sonuc = admin_supabase.table("profiles").select("*").eq("id", kullanici_id).limit(1).execute()
            profil = sonuc.data[0] if sonuc.data else {}
        except Exception as exc:
            logger.warning("Profil okunamadı, Auth verisi kullanılacak: %s", exc)

    return {
        "id": kullanici_id,
        "username": eposta,
        "company_name": profil.get("company_name") or "Pusula",
        "full_name": profil.get("full_name") or eposta or "Google kullanıcısı",
        "role": profil.get("role", "user"),
        "plan": profil.get("plan", "starter"),
    }


@router.post("/refresh")
@limiter.limit("10/minute")
def oturum_yenile(request: Request, response: Response, body: RefreshRequest):
    response.headers["Cache-Control"] = "no-store"
    if not public_supabase:
        raise HTTPException(status_code=503, detail="Supabase Auth yapılandırılmamış.")
    try:
        oturum = public_supabase.auth.refresh_session(body.refresh_token)
        if not oturum.session:
            raise HTTPException(status_code=401, detail="Oturum yenilenemedi.")
        return {
            "token": oturum.session.access_token,
            "refresh_token": oturum.session.refresh_token,
            "expires_at": oturum.session.expires_at,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Oturum yenilenemedi.") from exc


@router.post("/login")
@limiter.limit("5/minute")
def giris_yap(request: Request, response: Response, req: LoginRequest):
    response.headers["Cache-Control"] = "no-store"
    kullanici_adi = req.username.strip().lower()

    try:
        if public_supabase:
            oturum = public_supabase.auth.sign_in_with_password({"email": kullanici_adi, "password": req.password})
            if not oturum.user or not oturum.session:
                raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı.")

            profil = {}
            if admin_supabase:
                try:
                    sonuc = admin_supabase.table("profiles").select("*").eq("id", str(oturum.user.id)).limit(1).execute()
                    profil = sonuc.data[0] if sonuc.data else {}
                except Exception as exc:
                    logger.warning("Profil okunamadı, Auth verisi kullanılacak: %s", exc)

            if profil and not profil.get("is_active", True):
                raise HTTPException(status_code=403, detail="Kullanıcı hesabı devre dışı.")

            kullanici = {
                "id": str(oturum.user.id),
                "username": oturum.user.email,
                "company_name": profil.get("company_name") or "Pusula",
                "full_name": profil.get("full_name") or oturum.user.email,
                "role": profil.get("role", "user"),
                "plan": profil.get("plan", "starter"),
            }
            return {
                "message": "Giriş başarılı.",
                "token": oturum.session.access_token,
                "refresh_token": oturum.session.refresh_token,
                "expires_at": oturum.session.expires_at,
                "user": kullanici,
            }

        gelistirici_eposta = (os.getenv("DEV_USER_EMAIL") or "").strip().lower()
        if settings.dev_mode and kullanici_adi == gelistirici_eposta and req.password == os.getenv("DEV_USER_PASSWORD"):
            token = create_access_token({"sub": "local-dev-user", "username": kullanici_adi})
            kullanici = {"id": "local-dev-user", "username": kullanici_adi, "company_name": "Yerel Geliştirme", "full_name": "Geliştirici"}
            return {"message": "Giriş başarılı.", "token": token, "refresh_token": None, "user": kullanici}

        raise HTTPException(status_code=503, detail="Supabase Auth yapılandırılmamış.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Giriş başarısız: %s", exc)
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı.") from exc


auth_config = kimlik_ayarlari
me = profil_bilgim
refresh = oturum_yenile
login = giris_yap
