from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.admin import require_admin
from core.database import get_async_db
from models.visitor_model import VisitorModel
from services.visitor_inbox_service import VisitorInboxService

router = APIRouter(prefix="/admin/visitors", tags=["Visitor Admin"])
gelen_kutusu_servisi = VisitorInboxService()
inbox_service = gelen_kutusu_servisi


@router.get("")
async def ziyaretcileri_listele(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    _: dict = Depends(require_admin),
):
    toplam = (await db.execute(select(func.count(VisitorModel.id)))).scalar_one()
    satirlar = (
        await db.execute(
            select(VisitorModel)
            .order_by(VisitorModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": toplam,
        "visitors": [
            {
                "id": satir.id,
                "country": satir.country,
                "city": satir.city,
                "company_candidate": satir.operator,
                "detection_method": satir.detection_method,
                "confidence": satir.confidence,
                "permission": satir.permission,
                "created_at": satir.created_at,
                "retention_until": satir.retention_until,
            }
            for satir in satirlar
        ],
    }


@router.get("/summary")
async def ziyaretci_ozeti(
    db: AsyncSession = Depends(get_async_db),
    _: dict = Depends(require_admin),
):
    toplam = (await db.execute(select(func.count(VisitorModel.id)))).scalar_one()
    kurumsal_sayisi = (
        await db.execute(
            select(func.count(VisitorModel.id)).where(VisitorModel.operator.is_not(None))
        )
    ).scalar_one()
    ulke_sayisi = (
        await db.execute(select(func.count(func.distinct(VisitorModel.country))))
    ).scalar_one()

    return {
        "total": toplam,
        "company_candidates": kurumsal_sayisi,
        "countries": ulke_sayisi,
    }


@router.delete("/expired")
async def suresi_dolan_ziyaretcileri_sil(
    db: AsyncSession = Depends(get_async_db),
    _: dict = Depends(require_admin),
):
    sonuc = await db.execute(
        delete(VisitorModel).where(VisitorModel.retention_until < datetime.now())
    )
    await db.commit()
    return {"deleted": getattr(sonuc, "rowcount", 0) or 0}


@router.get("/notifications")
async def bildirimleri_listele(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    unread_only: bool = False,
    db: AsyncSession = Depends(get_async_db),
    user: dict = Depends(require_admin),
):
    kullanici_id = user.get("id") or user.get("sub")
    return await gelen_kutusu_servisi.list_for_user(
        db,
        kullanici_id,
        page,
        page_size,
        unread_only,
    )


@router.post("/notifications/{notification_id}/read")
async def bildirimi_okundu_yap(
    notification_id: str,
    db: AsyncSession = Depends(get_async_db),
    user: dict = Depends(require_admin),
):
    kullanici_id = user.get("id") or user.get("sub")
    if not await gelen_kutusu_servisi.mark_read(db, kullanici_id, notification_id):
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    return {"status": "read"}


@router.post("/notifications/read-all")
async def tum_bildirimleri_okundu_yap(
    db: AsyncSession = Depends(get_async_db),
    user: dict = Depends(require_admin),
):
    kullanici_id = user.get("id") or user.get("sub")
    return {"updated": await gelen_kutusu_servisi.mark_all_read(db, kullanici_id)}


list_visitors = ziyaretcileri_listele
visitor_summary = ziyaretci_ozeti
delete_expired_visitors = suresi_dolan_ziyaretcileri_sil
list_notifications = bildirimleri_listele
mark_notification_read = bildirimi_okundu_yap
mark_all_notifications_read = tum_bildirimleri_okundu_yap
