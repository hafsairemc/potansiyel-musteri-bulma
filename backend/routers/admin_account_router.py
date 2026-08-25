from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.admin import require_admin
from core.database import get_async_db
from models.growth_model import AdminAction
from services.db import admin_supabase
from services.plan_service import PlanService

router = APIRouter(prefix="/admin/users", tags=["Account Admin"])


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: str | None = Field(default=None, min_length=1, max_length=50)
    role: str | None = Field(default=None, min_length=1, max_length=20)
    is_active: bool | None = None


KullaniciGuncelle = UserUpdate


@router.get("")
def kullanicilari_listele(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: dict = Depends(require_admin),
):
    if not admin_supabase:
        raise HTTPException(503, "Supabase yönetici bağlantısı yapılandırılmamış")

    baslangic = (page - 1) * page_size
    sonuc = (
        admin_supabase.table("profiles")
        .select("id,company_name,full_name,role,plan,is_active,created_at", count="exact")
        .order("created_at", desc=True)
        .range(baslangic, baslangic + page_size - 1)
        .execute()
    )
    return {
        "page": page,
        "page_size": page_size,
        "total": sonuc.count or 0,
        "users": sonuc.data or [],
    }


@router.patch("/{user_id}")
async def kullanici_guncelle(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin),
):
    if not admin_supabase:
        raise HTTPException(503, "Supabase yönetici bağlantısı yapılandırılmamış")

    degisiklikler = body.model_dump(exclude_none=True)
    if not degisiklikler:
        raise HTTPException(422, "En az bir alan gönderin")

    if "plan" in degisiklikler:
        degisiklikler["plan"] = PlanService.validate_plan(degisiklikler["plan"])

    if "role" in degisiklikler and degisiklikler["role"] not in {"user", "admin"}:
        raise HTTPException(422, "Rol user veya admin olmalıdır")

    yonetici_id = admin.get("id") or admin.get("sub")
    if user_id == yonetici_id and (
        degisiklikler.get("role") == "user" or degisiklikler.get("is_active") is False
    ):
        raise HTTPException(409, "Yönetici kendi yönetim erişimini kaldıramaz")

    sonuc = admin_supabase.table("profiles").update(degisiklikler).eq("id", user_id).execute()
    if not sonuc.data:
        raise HTTPException(404, "Kullanıcı bulunamadı")

    db.add(
        AdminAction(
            actor_user_id=yonetici_id,
            target_user_id=user_id,
            action="profile_updated",
            details=degisiklikler,
        )
    )
    await db.commit()
    return sonuc.data[0]


list_users = kullanicilari_listele
update_user = kullanici_guncelle
