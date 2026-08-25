from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_async_db
from core.security import get_current_user
from models.growth_model import DemandPost, DemandPostTarget
from models.product_model import ProductModel
from routers.intelligence_common import get_owned_record, urun_bul_veya_olustur
from schemas.growth_schema import ApprovalBody, DemandPostBody
from services.demand_publication_service import PLATFORM_PUBLISH_PAGES
from services.plan_service import PlanService
from services.task_queue import enqueue_demand_post

router = APIRouter(prefix="/demand-posts", tags=["Demand Publication"])


@router.post("", status_code=201)
@router.post("/", status_code=201)
async def talep_ilani_olustur(
    body: DemandPostBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "demand_posts")
    urun = await urun_bul_veya_olustur(db, user["sub"], body.product_id)

    desteklenmeyen = set(body.platforms) - set(PLATFORM_PUBLISH_PAGES)
    if desteklenmeyen:
        raise HTTPException(
            422, f"Desteklenmeyen platform: {', '.join(sorted(desteklenmeyen))}"
        )

    ulke = (body.target_country or "Türkiye").strip()
    baslik = (body.title or f"{urun.name_tr} Tedarik Talebi").strip()
    aciklama = (body.description or f"{ulke} pazarı için {body.quantity or 'Belirtilmedi'} miktarında {urun.name_tr} tedarik ve satın alma talebidir.").strip()

    ilan = DemandPost(
        user_id=user["sub"],
        product_id=urun.id,
        title=baslik,
        description=aciklama,
        quantity=body.quantity,
        target_country=ulke,
        deadline=(
            datetime.combine(body.deadline, datetime.min.time())
            if body.deadline
            else None
        ),
    )
    ilan.targets = [
        DemandPostTarget(platform=platform)
        for platform in dict.fromkeys(body.platforms)
    ]
    db.add(ilan)
    await db.commit()
    await db.refresh(ilan)

    return {"id": ilan.id, "status": ilan.status, "target_count": len(ilan.targets), "title": ilan.title}


@router.post("/{post_id}/approve")
async def talep_ilanini_onayla(
    post_id: str,
    body: ApprovalBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    ilan = await get_owned_record(db, DemandPost, post_id, user["sub"])
    if not body.confirm_send:
        raise HTTPException(422, "Yayınlama için açık kullanıcı onayı gereklidir")
    if ilan.status != "DRAFT":
        raise HTTPException(409, "Yalnız taslak talep onaylanabilir")

    ilan.status = "QUEUED"
    ilan.approved_at = datetime.utcnow()
    await db.commit()

    try:
        enqueue_demand_post(ilan.id)
    except Exception as exc:
        ilan.status = "DRAFT"
        ilan.approved_at = None
        await db.commit()
        raise HTTPException(503, "Yayınlama görevi kuyruğa alınamadı") from exc

    return {"id": ilan.id, "status": ilan.status}


@router.get("/{post_id}")
async def talep_ilani_durumu(
    post_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    ilan = await get_owned_record(db, DemandPost, post_id, user["sub"])
    hedefler = (
        (
            await db.execute(
                select(DemandPostTarget).where(DemandPostTarget.demand_post_id == ilan.id)
            )
        )
        .scalars()
        .all()
    )

    return {
        "id": ilan.id,
        "status": ilan.status,
        "targets": [
            {
                "platform": hedef.platform,
                "status": hedef.status,
                "publication_url": hedef.publication_url,
                "error": "Yayınlama tamamlanamadı" if hedef.error_message else None,
            }
            for hedef in hedefler
        ],
    }


create_demand_post = talep_ilani_olustur
approve_demand_post = talep_ilanini_onayla
demand_post_status = talep_ilani_durumu
