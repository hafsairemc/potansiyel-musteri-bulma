import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings

guvenlik = HTTPBearer(auto_error=False)


def _yetkisiz_hatasi(detay: str = "Geçersiz veya süresi dolmuş oturum") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detay,
        headers={"WWW-Authenticate": "Bearer"},
    )


def token_dogrula_ve_coz(token: str) -> dict:
    from services.auth import JWT_ALGORITHM, JWT_SECRET
    from services.db import admin_supabase, public_supabase

    try:
        if public_supabase:
            yanit = public_supabase.auth.get_user(token)
            if yanit is None or not yanit.user:
                raise _yetkisiz_hatasi()

            if admin_supabase:
                try:
                    profil = (
                        admin_supabase.table("profiles")
                        .select("is_active")
                        .eq("id", str(yanit.user.id))
                        .limit(1)
                        .execute()
                    )
                except Exception as exc:
                    raise HTTPException(
                        status_code=503, detail="Hesap durumu doğrulanamadı"
                    ) from exc

                profil_bilgisi = (
                    profil.data[0] if profil.data and isinstance(profil.data[0], dict) else {}
                )
                if not profil_bilgisi.get("is_active", True):
                    raise HTTPException(status_code=403, detail="Kullanıcı hesabı devre dışı")

            return {"sub": str(yanit.user.id), "email": yanit.user.email}

        if not settings.dev_mode or not JWT_SECRET:
            raise _yetkisiz_hatasi("Kimlik doğrulama yapılandırılmamış")

        icerik = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        kullanici_id = icerik.get("sub", icerik.get("id"))
        if not kullanici_id:
            raise _yetkisiz_hatasi()

        icerik["sub"] = kullanici_id
        return icerik

    except HTTPException:
        raise
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise _yetkisiz_hatasi()
    except Exception:
        raise _yetkisiz_hatasi()


def mevcut_kullanici(
    kimlik_bilgisi: HTTPAuthorizationCredentials | None = Depends(guvenlik),
) -> dict:
    token = kimlik_bilgisi.credentials if kimlik_bilgisi else None
    if token is None:
        raise _yetkisiz_hatasi("Yetkilendirme token'ı eksik")

    return token_dogrula_ve_coz(token)


security = guvenlik
_unauthorized = _yetkisiz_hatasi
decode_and_verify_token = token_dogrula_ve_coz
get_current_user = mevcut_kullanici
