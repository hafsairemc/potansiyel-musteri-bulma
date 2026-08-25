import os
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.concurrency import run_in_threadpool

from core.database import get_async_db
from core.security import get_current_user
from models.growth_model import EmailCampaign, EmailRecipient
from routers.intelligence_common import get_owned_record
from schemas.growth_schema import ApprovalBody, CampaignBody, EmailDeliveryEventBody
from services.email_campaign_service import campaign_metrics, smtp_is_configured
from services.email_event_service import EmailEventError, EmailEventService, valid_signature
from services.email_reply_service import EmailReplyError, EmailReplyService
from services.plan_service import PlanService
from services.task_queue import enqueue_email_campaign

router = APIRouter(tags=["Email Campaigns"])

TAKIP_PIKSELI = bytes.fromhex(
    "47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b"
)
TRACKING_PIXEL = TAKIP_PIKSELI


def eposta_temizle(deger: str) -> str:
    duzenlenmis = deger.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", duzenlenmis):
        raise HTTPException(422, f"Geçersiz e-posta: {deger}")
    return duzenlenmis


clean_email = eposta_temizle


@router.post("/email/events", include_in_schema=False)
async def eposta_olayi_al(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    gizli_anahtar = os.getenv("EMAIL_EVENT_WEBHOOK_SECRET", "").strip()
    if not gizli_anahtar:
        raise HTTPException(503, "E-posta olay webhook'u yapılandırılmamış")

    govde = await request.body()
    imza = request.headers.get("X-Pusula-Signature", "")
    if not valid_signature(govde, imza, gizli_anahtar):
        raise HTTPException(401, "Geçersiz webhook imzası")

    try:
        olay = EmailDeliveryEventBody.model_validate_json(govde)
    except ValidationError as exc:
        raise HTTPException(422, "Geçersiz e-posta olay verisi") from exc

    try:
        durum = await EmailEventService().apply(db, olay)
    except EmailEventError as exc:
        raise HTTPException(404, str(exc)) from exc

    return {"status": durum}


@router.post("/email-campaigns", status_code=201)
async def eposta_kampanyasi_olustur(
    body: CampaignBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "email_campaigns")
    epostalar = [eposta_temizle(item.email) for item in body.recipients]
    if len(epostalar) != len(set(epostalar)):
        raise HTTPException(422, "Aynı alıcı kampanyaya bir kez eklenebilir")

    kampanya = EmailCampaign(
        user_id=user["sub"],
        name=body.name.strip(),
        subject=body.subject.strip(),
        body=body.body.strip(),
        reply_to=eposta_temizle(body.reply_to) if body.reply_to else None,
    )
    kampanya.recipients = [
        EmailRecipient(
            email=eposta,
            full_name=item.full_name,
            company_name=item.company_name,
        )
        for eposta, item in zip(epostalar, body.recipients)
    ]
    db.add(kampanya)
    await db.commit()
    await db.refresh(kampanya)

    return {
        "id": kampanya.id,
        "status": kampanya.status,
        "recipient_count": len(epostalar),
    }


@router.get("/email-campaigns")
async def eposta_kampanyalarini_listele(
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    satirlar = (
        await db.execute(
            select(EmailCampaign, func.count(EmailRecipient.id))
            .outerjoin(EmailRecipient)
            .where(EmailCampaign.user_id == user["sub"])
            .group_by(EmailCampaign.id)
            .order_by(EmailCampaign.created_at.desc())
        )
    ).all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "subject": item.subject,
            "status": item.status,
            "recipient_count": sayi,
        }
        for item, sayi in satirlar
    ]


@router.post("/email-campaigns/{campaign_id}/approve")
async def eposta_kampanyasini_onayla(
    campaign_id: str,
    body: ApprovalBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kampanya = await get_owned_record(db, EmailCampaign, campaign_id, user["sub"])
    if not body.confirm_send:
        raise HTTPException(422, "Gönderim için açık kullanıcı onayı gereklidir")
    if kampanya.status != "DRAFT":
        raise HTTPException(409, "Yalnız taslak kampanya onaylanabilir")
    if not smtp_is_configured():
        raise HTTPException(
            503, "SMTP bilgileri yapılandırılmamış; kampanya taslak olarak korundu"
        )

    kampanya.status = "QUEUED"
    kampanya.approved_at = datetime.utcnow()
    await db.commit()

    try:
        enqueue_email_campaign(kampanya.id)
    except Exception as exc:
        kampanya.status = "DRAFT"
        kampanya.approved_at = None
        await db.commit()
        raise HTTPException(503, "E-posta görevi kuyruğa alınamadı") from exc

    return {"id": kampanya.id, "status": kampanya.status}


@router.get("/email-campaigns/{campaign_id}")
async def eposta_kampanya_durumu(
    campaign_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kampanya = await get_owned_record(db, EmailCampaign, campaign_id, user["sub"])
    alicilar = (
        (
            await db.execute(
                select(EmailRecipient).where(EmailRecipient.campaign_id == kampanya.id)
            )
        )
        .scalars()
        .all()
    )

    return {
        "id": kampanya.id,
        "status": kampanya.status,
        "metrics": campaign_metrics(alicilar),
        "recipients": [
            {
                "email": item.email,
                "status": item.status,
                "error": "Gönderilemedi" if item.error_message else None,
                "sent_at": item.sent_at,
                "opened_at": item.opened_at,
                "open_count": item.open_count,
                "unsubscribed_at": item.unsubscribed_at,
                "replied_at": item.replied_at,
                "reply_subject": item.reply_subject,
                "delivery_status": item.delivery_status,
                "delivered_at": item.delivered_at,
                "bounced_at": item.bounced_at,
                "complained_at": item.complained_at,
                "bounce_reason": item.bounce_reason,
            }
            for item in alicilar
        ],
    }


@router.post("/email-campaigns/{campaign_id}/sync-replies")
async def eposta_yanitlarini_esitle(
    campaign_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kampanya = await get_owned_record(db, EmailCampaign, campaign_id, user["sub"])
    alicilar = (
        (
            await db.execute(
                select(EmailRecipient).where(EmailRecipient.campaign_id == kampanya.id)
            )
        )
        .scalars()
        .all()
    )

    try:
        esitleme_sonucu = await run_in_threadpool(
            EmailReplyService().sync, kampanya, alicilar
        )
    except EmailReplyError as exc:
        raise HTTPException(503, str(exc)) from exc

    await db.commit()
    return {
        "matched": esitleme_sonucu.replies,
        "bounces": esitleme_sonucu.bounces,
        "metrics": campaign_metrics(alicilar),
    }


@router.get("/email/unsubscribe/{token}", response_class=HTMLResponse)
async def eposta_aboneliginden_cik(token: str, db: AsyncSession = Depends(get_async_db)):
    alici = (
        await db.execute(
            select(EmailRecipient).where(EmailRecipient.unsubscribe_token == token)
        )
    ).scalar_one_or_none()

    if alici is None:
        raise HTTPException(404, "Bağlantı geçersiz")

    alici.unsubscribed_at = alici.unsubscribed_at or datetime.utcnow()
    alici.status = "UNSUBSCRIBED"
    await db.commit()

    return (
        "<h1>Abonelikten çıkıldı</h1>"
        "<p>Bu kampanyadan başka e-posta almayacaksınız.</p>"
    )


@router.get("/email/open/{token}.gif", include_in_schema=False)
async def eposta_acilmasini_takip_et(token: str, db: AsyncSession = Depends(get_async_db)):
    alici = (
        await db.execute(
            select(EmailRecipient).where(EmailRecipient.tracking_token == token)
        )
    ).scalar_one_or_none()

    if alici and alici.sent_at:
        simdi = datetime.utcnow()
        alici.opened_at = alici.opened_at or simdi
        alici.last_opened_at = simdi
        alici.open_count = (alici.open_count or 0) + 1
        await db.commit()

    return Response(
        content=TAKIP_PIKSELI,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


receive_email_event = eposta_olayi_al
create_email_campaign = eposta_kampanyasi_olustur
list_email_campaigns = eposta_kampanyalarini_listele
approve_email_campaign = eposta_kampanyasini_onayla
email_campaign_status = eposta_kampanya_durumu
sync_email_replies = eposta_yanitlarini_esitle
unsubscribe_email = eposta_aboneliginden_cik
track_email_open = eposta_acilmasini_takip_et
