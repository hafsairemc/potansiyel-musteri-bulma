import os
import tempfile
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from core.config import settings
from core.database import get_async_db
from core.security import get_current_user
from models.crawler_model import (
    CrawlerCompany,
    CrawlerSearchJob,
    CrawlerSearchResult,
    SearchBatch,
)
from models.intelligence_model import (
    AssistantConversation,
    AssistantMessage,
    FairAnalysis,
    FairEntry,
    RFQOpportunity,
    RFQSearch,
)
from models.product_model import ProductModel
from routers.intelligence_common import get_owned_record, queue_record, urun_bul_veya_olustur
from services.assistant_service import answer_question
from services.db import admin_supabase
from services.domain_input_service import DomainInputService
from services.fair_file_service import FairFileError, FairFileService
from services.fair_page_service import FairPageService
from services.fair_source_service import FairSourceError, FairSourceService
from services.intelligence_export_service import IntelligenceExportService
from services.intelligence_service import export_rows, read_fair_file
from services.plan_service import PlanService
from services.public_error_service import PublicErrorService
from services.search_source_service import SearchSourceService
from services.task_queue import (
    enqueue_fair_analysis,
    enqueue_rfq_search,
)

router = APIRouter(tags=["Intelligence Modules"])


def gecici_disa_aktarma_yaniti(dosya_yolu: str, dosya_adi: str) -> FileResponse:
    return FileResponse(
        dosya_yolu,
        filename=dosya_adi,
        background=BackgroundTask(Path(dosya_yolu).unlink, missing_ok=True),
    )


temporary_export_response = gecici_disa_aktarma_yaniti


def kamusal_arama_saglayici_kontrol():
    hazir, mesaj = SearchSourceService().status("google_web")
    if not hazir:
        raise HTTPException(503, f"Kamusal web araması yapılandırılmamış. {mesaj}")


require_public_search_provider = kamusal_arama_saglayici_kontrol


class RFQCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    target_country: str = Field(default="Türkiye", min_length=2, max_length=100)
    date_from: date | None = None


class MappingBody(BaseModel):
    mapping: dict[str, str] = Field(min_length=1, max_length=8)


class MessageBody(BaseModel):
    content: str = Field(min_length=1, max_length=1500)


class FairListBody(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    entries: str = Field(min_length=2, max_length=120000)


class FairUrlBody(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    source_url: str = Field(min_length=8, max_length=2000)


AlimTalebiOlustur = RFQCreate
SutunEslemeGovdesi = MappingBody
MesajGovdesi = MessageBody
FuarListeGovdesi = FairListBody
FuarUrlGovdesi = FairUrlBody


@router.post("/rfq-searches", status_code=201)
async def alim_talebi_olustur(
    body: RFQCreate,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "rfq")
    urun = await urun_bul_veya_olustur(db, user["sub"], body.product_id)

    kayit = RFQSearch(
        user_id=user["sub"],
        product_id=urun.id,
        target_country=body.target_country.strip() or "Türkiye",
        date_from=datetime.combine(body.date_from, datetime.min.time()) if body.date_from else None,
    )
    db.add(kayit)
    await db.commit()
    await db.refresh(kayit)
    return {"id": kayit.id, "status": kayit.status}


@router.post("/rfq-searches/{record_id}/start")
async def alim_talebi_baslat(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kayit = await get_owned_record(db, RFQSearch, record_id, user["sub"])
    if kayit.status not in ("PENDING", "FAILED"):
        raise HTTPException(409, "Bu RFQ araması zaten başlatılmış")
    kamusal_arama_saglayici_kontrol()
    await queue_record(db, kayit, enqueue_rfq_search)
    return {"id": kayit.id, "status": "QUEUED"}


@router.get("/rfq-searches/{record_id}/status")
async def alim_talebi_durumu(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kayit = await get_owned_record(db, RFQSearch, record_id, user["sub"])
    adet = (
        await db.execute(
            select(func.count(RFQOpportunity.id)).where(RFQOpportunity.rfq_search_id == kayit.id)
        )
    ).scalar_one()
    return {
        "id": kayit.id,
        "status": kayit.status,
        "progress": kayit.progress,
        "result_count": adet,
        "error": PublicErrorService.message(kayit.error_code, bool(kayit.error_message)),
    }


@router.get("/rfq-searches/{record_id}/results")
async def alim_talebi_sonuclari(
    record_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kayit = await get_owned_record(db, RFQSearch, record_id, user["sub"])
    toplam = (
        await db.execute(
            select(func.count(RFQOpportunity.id)).where(RFQOpportunity.rfq_search_id == kayit.id)
        )
    ).scalar_one()
    satirlar = (
        await db.execute(
            select(RFQOpportunity)
            .where(RFQOpportunity.rfq_search_id == kayit.id)
            .order_by(RFQOpportunity.relevance_score.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": toplam,
        "results": [
            {
                "title": r.title,
                "buyer_name": r.buyer_name,
                "country": r.country,
                "quantity": r.quantity,
                "deadline": r.deadline,
                "description": r.description,
                "platform": r.platform,
                "source_url": r.source_url,
                "access_status": r.access_status,
                "relevance_score": r.relevance_score,
                "confidence_score": r.confidence_score,
                "match_reason": r.match_reason,
            }
            for r in satirlar
        ],
    }


@router.post("/rfq-searches/{record_id}/exports")
async def alim_talebi_disa_aktar(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    await get_owned_record(db, RFQSearch, record_id, user["sub"])
    satirlar = (
        await db.execute(select(RFQOpportunity).where(RFQOpportunity.rfq_search_id == record_id))
    ).scalars().all()
    dosya_yolu = export_rows(IntelligenceExportService.rfq(satirlar), f"rfq-{record_id}")
    return gecici_disa_aktarma_yaniti(dosya_yolu, "pusula-rfq.xlsx")


async def fuar_analizi_olustur_ortak(
    product_id: str,
    filename: str,
    content: bytes,
    content_type: str,
    db: AsyncSession,
    user: dict,
    mapping: dict[str, str] | None = None,
) -> dict:
    PlanService().ensure_module(user["sub"], "fair")
    urun = await urun_bul_veya_olustur(db, user["sub"], product_id)

    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Dosya en fazla {settings.max_upload_mb} MB olabilir")

    dogrulayici = FairFileService()
    try:
        uzanti = dogrulayici.validate_content(filename, content)
    except FairFileError as exc:
        raise HTTPException(422, str(exc)) from exc

    gecici_yol = os.path.join(tempfile.gettempdir(), f"fair-{uuid.uuid4()}{uzanti}")
    try:
        with open(gecici_yol, "wb") as akis:
            akis.write(content)
        tablo = read_fair_file(gecici_yol)
        sutunlar = dogrulayici.validate_columns(tablo.columns)
        toplam_satir = len(tablo)
    except Exception as exc:
        Path(gecici_yol).unlink(missing_ok=True)
        raise HTTPException(422, "Dosya okunamadı. Geçerli bir XLSX/CSV yükleyin") from exc

    saklanan_yol = gecici_yol
    if admin_supabase:
        nesne_adi = f"{user['sub']}/fair/{uuid.uuid4()}{uzanti}"
        try:
            admin_supabase.storage.from_(settings.reports_bucket).upload(
                nesne_adi,
                content,
                {"content-type": content_type, "upsert": "false"},
            )
        except Exception as exc:
            Path(gecici_yol).unlink(missing_ok=True)
            raise HTTPException(503, "Fuar dosyası güvenli depoya yüklenemedi") from exc
        saklanan_yol = f"storage:{nesne_adi}"
        Path(gecici_yol).unlink(missing_ok=True)
    elif os.getenv("TASK_QUEUE_MODE", "celery").lower() != "inline":
        Path(gecici_yol).unlink(missing_ok=True)
        raise HTTPException(503, "Fuar dosyaları için Supabase Storage yapılandırılmamış")

    kayit = FairAnalysis(
        user_id=user["sub"],
        product_id=product_id,
        filename=Path(filename).name,
        file_path=saklanan_yol,
        source_columns=sutunlar,
        total_rows=toplam_satir,
        column_mapping=mapping or {},
        status="MAPPED" if mapping else "UPLOADED",
    )
    db.add(kayit)
    await db.commit()
    await db.refresh(kayit)
    return {"id": kayit.id, "status": kayit.status, "columns": sutunlar, "total_rows": toplam_satir}


create_fair_analysis = fuar_analizi_olustur_ortak


@router.post("/fair-analyses", status_code=201)
async def fuar_analizi_olustur_dosya(
    product_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    icerik = await file.read()
    return await fuar_analizi_olustur_ortak(
        product_id=product_id,
        filename=file.filename or "fuar.xlsx",
        content=icerik,
        content_type=file.content_type or "application/octet-stream",
        db=db,
        user=user,
    )


@router.post("/fair-analyses/from-list", status_code=201)
async def fuar_analizi_olustur_liste(
    body: FairListBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    try:
        icerik, _ = FairSourceService().build_csv(body.entries)
    except FairSourceError as exc:
        raise HTTPException(422, str(exc)) from exc

    return await fuar_analizi_olustur_ortak(
        product_id=body.product_id,
        filename="katilimci-listesi.csv",
        content=icerik,
        content_type="text/csv; charset=utf-8",
        db=db,
        user=user,
        mapping={"company_name": "Firma Adı", "website": "Website"},
    )


@router.post("/fair-analyses/from-url")
async def fuar_analizi_olustur_url(
    body: FairUrlBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "fair")
    urun = (
        await db.execute(
            select(ProductModel).where(
                ProductModel.id == body.product_id,
                ProductModel.user_id == user["sub"],
            )
        )
    ).scalar_one_or_none()
    if not urun:
        raise HTTPException(404, "Ürün bulunamadı")

    sonuc = await run_in_threadpool(FairPageService().extract, body.source_url)
    if sonuc.access_status != "public":
        return {
            "status": "BLOCKED",
            "access_status": sonuc.access_status,
            "source_url": sonuc.source_url,
            "detail": "Sayfa açık olarak taranamadı; CAPTCHA veya giriş koruması aşılmadı.",
        }
    if not sonuc.entries:
        return {
            "status": "EMPTY",
            "access_status": "public",
            "source_url": sonuc.source_url,
            "detail": "Açık sayfada katılımcı profili bulunamadı. Listeyi yapıştırarak devam edebilirsiniz.",
        }

    kaynak_metin = "\n".join(
        f"{isim} | {web}" if web else isim for isim, web in sonuc.entries
    )
    icerik, _ = FairSourceService().build_csv(kaynak_metin)
    yanit = await fuar_analizi_olustur_ortak(
        product_id=body.product_id,
        filename="fuar-sayfasi-katilimcilari.csv",
        content=icerik,
        content_type="text/csv; charset=utf-8",
        db=db,
        user=user,
        mapping={"company_name": "Firma Adı", "website": "Website"},
    )
    return {**yanit, "access_status": "public", "source_url": sonuc.source_url}


@router.post("/fair-analyses/{record_id}/column-mapping")
async def fuar_sutun_esle(
    record_id: str,
    body: MappingBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kayit = await get_owned_record(db, FairAnalysis, record_id, user["sub"])
    try:
        kayit.column_mapping = FairFileService().validate_mapping(
            body.mapping, kayit.source_columns or []
        )
    except FairFileError as exc:
        raise HTTPException(422, str(exc)) from exc

    kayit.status = "MAPPED"
    await db.commit()
    return {"id": kayit.id, "status": kayit.status}


@router.post("/fair-analyses/{record_id}/start")
async def fuar_analizi_baslat(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kayit = await get_owned_record(db, FairAnalysis, record_id, user["sub"])
    if not kayit.column_mapping.get("company_name"):
        raise HTTPException(409, "Önce sütun eşlemesi yapılmalıdır")
    if kayit.status not in ("MAPPED", "FAILED"):
        raise HTTPException(409, "Bu fuar analizi zaten başlatılmış")
    await queue_record(db, kayit, enqueue_fair_analysis)
    return {"id": kayit.id, "status": "QUEUED"}


@router.get("/fair-analyses/{record_id}/status")
async def fuar_analizi_durumu(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kayit = await get_owned_record(db, FairAnalysis, record_id, user["sub"])
    adet = (
        await db.execute(
            select(func.count(FairEntry.id)).where(FairEntry.fair_analysis_id == kayit.id)
        )
    ).scalar_one()
    return {
        "id": kayit.id,
        "status": kayit.status,
        "progress": kayit.progress,
        "result_count": adet,
        "total_rows": kayit.total_rows,
        "processed_rows": kayit.processed_rows,
        "duplicate_rows": kayit.duplicate_rows,
        "error_code": kayit.error_code,
        "error": PublicErrorService.message(kayit.error_code, bool(kayit.error_message)),
    }


@router.get("/fair-analyses/{record_id}/results")
async def fuar_analizi_sonuclari(
    record_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    await get_owned_record(db, FairAnalysis, record_id, user["sub"])
    toplam = (
        await db.execute(
            select(func.count(FairEntry.id)).where(FairEntry.fair_analysis_id == record_id)
        )
    ).scalar_one()
    satirlar = (
        await db.execute(
            select(FairEntry)
            .where(FairEntry.fair_analysis_id == record_id)
            .order_by(FairEntry.relevance_score.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": toplam,
        "results": [
            {
                "company_name": r.company_name,
                "website": r.website,
                "country": r.country,
                "sector": r.sector,
                "email": r.email,
                "phone": r.phone,
                "access_status": r.access_status,
                "relevance_score": r.relevance_score,
                "buyer_score": r.buyer_score,
                "classification": r.classification,
                "matched_terms": r.matched_terms,
                "match_reason": r.match_reason,
            }
            for r in satirlar
        ],
    }


@router.post("/fair-analyses/{record_id}/exports")
async def fuar_analizi_disa_aktar(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    await get_owned_record(db, FairAnalysis, record_id, user["sub"])
    satirlar = (
        await db.execute(select(FairEntry).where(FairEntry.fair_analysis_id == record_id))
    ).scalars().all()
    dosya_yolu = export_rows(IntelligenceExportService.fair(satirlar), f"fair-{record_id}")
    return gecici_disa_aktarma_yaniti(dosya_yolu, "pusula-fuar-analizi.xlsx")


@router.post("/assistant/conversations", status_code=201)
async def asistan_sohbeti_olustur(
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    PlanService().ensure_module(user["sub"], "assistant")
    kayit = AssistantConversation(user_id=user["sub"])
    db.add(kayit)
    await db.commit()
    await db.refresh(kayit)
    return {"id": kayit.id, "title": kayit.title}


@router.get("/assistant/conversations/{record_id}")
async def asistan_sohbeti_getir(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    await get_owned_record(db, AssistantConversation, record_id, user["sub"])
    satirlar = (
        await db.execute(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == record_id)
            .order_by(AssistantMessage.created_at)
        )
    ).scalars().all()
    return {
        "id": record_id,
        "messages": [
            {"role": m.role, "content": m.content, "mode": m.mode}
            for m in satirlar
        ],
    }


@router.post("/assistant/conversations/{record_id}/messages")
async def asistana_mesaj_gonder(
    record_id: str,
    body: MessageBody,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    sohbet = await get_owned_record(db, AssistantConversation, record_id, user["sub"])
    bugun = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )

    gunluk_mesaj_sayisi = (
        await db.execute(
            select(func.count(AssistantMessage.id))
            .join(AssistantConversation)
            .where(
                AssistantConversation.user_id == user["sub"],
                AssistantMessage.role == "user",
                AssistantMessage.created_at >= bugun,
            )
        )
    ).scalar_one()

    if gunluk_mesaj_sayisi >= 100:
        raise HTTPException(429, "Asistan mesaj limitine ulaşıldı")

    arama_sayisi = (
        await db.execute(select(func.count(SearchBatch.id)).where(SearchBatch.user_id == user["sub"]))
    ).scalar_one()
    rfq_sayisi = (
        await db.execute(
            select(func.count(RFQOpportunity.id))
            .join(RFQSearch)
            .where(RFQSearch.user_id == user["sub"])
        )
    ).scalar_one()
    fuar_sayisi = (
        await db.execute(
            select(func.count(FairEntry.id))
            .join(FairAnalysis)
            .where(FairAnalysis.user_id == user["sub"])
        )
    ).scalar_one()

    ozet = (
        f"Hesabınızda {arama_sayisi} arama, {rfq_sayisi} RFQ "
        f"ve {fuar_sayisi} fuar satırı bulunuyor."
    )

    gecmis_satirlari = (
        await db.execute(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == sohbet.id)
            .order_by(AssistantMessage.created_at.desc())
            .limit(8)
        )
    ).scalars().all()

    gecmis = [
        {"role": mesaj.role, "content": mesaj.content}
        for mesaj in reversed(gecmis_satirlari)
    ]

    cevap, mod = answer_question(body.content, ozet, gecmis)
    db.add(AssistantMessage(conversation_id=sohbet.id, role="user", content=body.content, mode=mod))
    db.add(AssistantMessage(conversation_id=sohbet.id, role="assistant", content=cevap, mode=mod))
    await db.commit()

    return {"role": "assistant", "content": cevap, "mode": mod}


@router.delete("/assistant/conversations/{record_id}", status_code=204)
async def asistan_sohbeti_sil(
    record_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(get_current_user),
):
    kayit = await get_owned_record(db, AssistantConversation, record_id, user["sub"])
    await db.delete(kayit)
    await db.commit()


create_rfq = alim_talebi_olustur
start_rfq = alim_talebi_baslat
rfq_status = alim_talebi_durumu
rfq_results = alim_talebi_sonuclari
export_rfq = alim_talebi_disa_aktar
upload_fair = fuar_analizi_olustur_dosya
create_fair_from_list = fuar_analizi_olustur_liste
create_fair_from_url = fuar_analizi_olustur_url
map_fair = fuar_sutun_esle
start_fair = fuar_analizi_baslat
fair_status = fuar_analizi_durumu
fair_results = fuar_analizi_sonuclari
export_fair = fuar_analizi_disa_aktar
create_conversation = asistan_sohbeti_olustur
get_conversation = asistan_sohbeti_getir
send_message = asistana_mesaj_gonder
delete_conversation = asistan_sohbeti_sil
