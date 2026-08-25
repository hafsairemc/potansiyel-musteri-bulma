import math
import os
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_async_db
from core.security import get_current_user
from models.crawler_model import CrawlerCompany, CrawlerSearchJob, CrawlerSearchResult, SearchBatch, SearchExport
from models.product_model import ProductModel
from schemas.search_batch_schema import (
    BatchStatusResponse,
    ExportCreated,
    ExportRequest,
    ExportStatus,
    ResultsPage,
    SearchBatchCreate,
    SearchBatchCreated,
)
from services.db import admin_supabase
from services.plan_service import PlanService
from services.public_error_service import PublicErrorService
from services.search_result_filter_service import result_conditions
from services.search_scope_service import SearchScopeError, SearchScopeService
from services.search_source_service import SearchSourceService
from services.task_queue import enqueue_export, enqueue_job

router = APIRouter(tags=["Search Batches"])


async def _kullaniciya_ait_grup(db: AsyncSession, batch_id: str, user_id: str) -> SearchBatch:
    sorgu = select(SearchBatch).where(
        SearchBatch.id == batch_id,
        SearchBatch.user_id == user_id,
    )
    sonuc = await db.execute(sorgu)
    grup = sonuc.scalar_one_or_none()
    if not grup:
        raise HTTPException(status_code=404, detail="Arama grubu bulunamadı")
    return grup


_owned_batch = _kullaniciya_ait_grup


@router.post("/search-batches", response_model=SearchBatchCreated, status_code=201)
async def arama_grubu_olustur(
    body: SearchBatchCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    kullanici_id = current_user["sub"]
    plan_servisi = PlanService()
    plan_servisi.ensure_module(kullanici_id, "customer_search")

    if plan_servisi.is_enforced():
        haklar = plan_servisi.entitlements(kullanici_id)
        aylik_limit = haklar["monthly_searches"]
        if aylik_limit is not None:
            ay_basi = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            kullanilan = (
                await db.execute(
                    select(func.count(SearchBatch.id)).where(
                        SearchBatch.user_id == kullanici_id,
                        SearchBatch.created_at >= ay_basi,
                    )
                )
            ).scalar_one()
            if kullanilan >= aylik_limit:
                raise HTTPException(status_code=429, detail="Aylık arama limitinize ulaştınız")

    urun_sorgusu = select(ProductModel).where(
        ProductModel.id == body.product_id,
        ProductModel.user_id == kullanici_id,
    )
    urun_sonucu = await db.execute(urun_sorgusu)
    urun = urun_sonucu.scalar_one_or_none()
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    try:
        ulkeler = SearchScopeService().countries(body.target_countries, kullanici_id)
    except SearchScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    kaynaklar = list(dict.fromkeys(body.sources))
    hazir_olmayan_kaynaklar = SearchSourceService().unavailable(kaynaklar)
    if len(hazir_olmayan_kaynaklar) == len(kaynaklar):
        detaylar = "; ".join(f"{k}: {m}" for k, m in hazir_olmayan_kaynaklar.items())
        raise HTTPException(status_code=422, detail=f"Seçilen arama kaynakları hazır değil. {detaylar}")

    ikililer = [(ulke, kaynak) for ulke in ulkeler for kaynak in kaynaklar]
    calismayacak_gorev_sayisi = sum(kaynak in hazir_olmayan_kaynaklar for _, kaynak in ikililer)

    grup = SearchBatch(
        user_id=kullanici_id,
        product_id=body.product_id,
        total_jobs=len(ikililer),
        failed_jobs=calismayacak_gorev_sayisi,
        progress=int(calismayacak_gorev_sayisi / len(ikililer) * 100),
    )
    db.add(grup)
    await db.flush()

    gorevler = []
    motor_isimleri = {
        "google_web": "Google",
        "yandex_web": "Yandex",
        "google_maps": "Google Maps",
        "b2b_platform": "B2B Platformları",
    }

    for ulke, kaynak in ikililer:
        hata_mesaji = hazir_olmayan_kaynaklar.get(kaynak)
        gorevler.append(
            CrawlerSearchJob(
                user_id=kullanici_id,
                product_id=body.product_id,
                batch_id=grup.id,
                search_query=urun.name_en or urun.name_tr,
                target_country=ulke,
                search_engine=motor_isimleri[kaynak],
                source=kaynak,
                status="FAILED" if hata_mesaji else "PENDING",
                progress=100 if hata_mesaji else 0,
                error_code="PROVIDER_NOT_CONFIGURED" if hata_mesaji else None,
                error_message=hata_mesaji,
            )
        )
    db.add_all(gorevler)
    await db.flush()

    grup_id = grup.id
    gorev_idleri = [g.id for g in gorevler]
    await db.commit()

    return SearchBatchCreated(id=grup_id, status="PENDING", total_jobs=len(gorevler), job_ids=gorev_idleri)


@router.post("/search-batches/{batch_id}/start")
async def arama_grubunu_baslat(
    batch_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    grup = await _kullaniciya_ait_grup(db, batch_id, current_user["sub"])
    sonuc = await db.execute(
        select(CrawlerSearchJob).where(
            CrawlerSearchJob.batch_id == grup.id,
            CrawlerSearchJob.status == "PENDING",
        )
    )
    gorevler = sonuc.scalars().all()
    if not gorevler:
        raise HTTPException(status_code=409, detail="Başlatılacak bekleyen görev yok")

    gorev_idleri = [g.id for g in gorevler]
    grup_id = grup.id
    grup.status = "RUNNING"
    await db.commit()

    try:
        for gid in gorev_idleri:
            enqueue_job(gid)
    except Exception as exc:
        grup.status = "FAILED"
        await db.commit()
        raise HTTPException(status_code=503, detail="Görev kuyruğuna şu anda ulaşılamıyor") from exc

    return {"id": grup_id, "status": "RUNNING", "queued_jobs": len(gorev_idleri)}


@router.get("/search-batches/{batch_id}/status", response_model=BatchStatusResponse)
async def arama_grubu_durumu(
    batch_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    grup = await _kullaniciya_ait_grup(db, batch_id, current_user["sub"])
    sonuc = await db.execute(select(CrawlerSearchJob).where(CrawlerSearchJob.batch_id == grup.id))
    gorevler = sonuc.scalars().all()

    bekleyen_idleri = [
        g.id for g in gorevler if grup.status == "RUNNING" and g.status == "PENDING" and not g.attempt_count
    ]
    if bekleyen_idleri:
        for g in gorevler:
            if g.id in bekleyen_idleri:
                g.status = "QUEUED"
        await db.commit()
        for gid in bekleyen_idleri:
            enqueue_job(gid)

    return BatchStatusResponse(
        id=grup.id,
        status=grup.status,
        progress=grup.progress,
        total_jobs=grup.total_jobs,
        completed_jobs=grup.completed_jobs,
        failed_jobs=grup.failed_jobs,
        jobs=[
            {
                "id": j.id,
                "country": j.target_country,
                "source": j.source,
                "status": j.status,
                "progress": j.progress,
                "result_count": j.successful_companies or 0,
                "error_code": j.error_code,
                "error": PublicErrorService.message(j.error_code, bool(j.error_message)),
            }
            for j in gorevler
        ],
    )


@router.get("/search-batches/{batch_id}/results", response_model=ResultsPage)
async def arama_grubu_sonuclari(
    batch_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    country: str | None = None,
    city: str | None = None,
    source: str | None = None,
    platform: str | None = None,
    customer_type: str | None = None,
    sector_match: str | None = Query(None, pattern="^(main|sub)$"),
    q: str | None = Query(None, max_length=100),
    min_score: int = Query(0, ge=0, le=100),
    min_relevance: int = Query(45, ge=0, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    grup = await _kullaniciya_ait_grup(db, batch_id, current_user["sub"])
    kosullar = result_conditions(
        grup.id,
        {
            "country": country,
            "city": city,
            "source": source,
            "platform": platform,
            "customer_type": customer_type,
            "sector_match": sector_match,
            "min_score": min_score,
            "min_relevance": min_relevance,
            "q": q,
        },
    )

    toplam_sorgusu = (
        select(func.count(CrawlerSearchResult.id))
        .join(CrawlerSearchJob)
        .join(CrawlerCompany)
        .where(*kosullar)
    )
    toplam = (await db.execute(toplam_sorgusu)).scalar_one()

    ana_sorgu = (
        select(CrawlerSearchResult, CrawlerCompany, CrawlerSearchJob)
        .join(CrawlerSearchJob)
        .join(CrawlerCompany)
        .where(*kosullar)
        .order_by(CrawlerSearchResult.score.desc(), CrawlerSearchResult.position)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    satirlar = (await db.execute(ana_sorgu)).all()

    sonuclar = [
        {
            "company_name": c.name or "Bilinmiyor",
            "country": c.country or j.target_country or "—",
            "city": c.city or "",
            "email": c.email or "",
            "email_verified": c.email_status == "verified",
            "email_status": c.email_status,
            "email_source_url": c.email_source_url,
            "phone": c.phone or "",
            "address": c.address or "",
            "website": r.source_url,
            "source": r.source,
            "platform": r.platform or "",
            "search_query": r.search_query or j.search_query,
            "sector_match": r.sector_match,
            "customer_type": r.customer_type,
            "score": r.score,
            "relevance_score": r.relevance_score,
            "buyer_score": r.buyer_score,
            "matched_terms": r.matched_terms or [],
            "category_path": r.category_path or "",
            "confidence_score": r.confidence_score,
            "match_reason": r.match_reason or "",
        }
        for r, c, j in satirlar
    ]

    ulkeler_sorgusu = (
        select(func.count(func.distinct(func.coalesce(CrawlerCompany.country, CrawlerSearchJob.target_country))))
        .select_from(CrawlerSearchResult)
        .join(CrawlerSearchJob)
        .join(CrawlerCompany)
        .where(*kosullar)
    )
    ulke_sayisi = (await db.execute(ulkeler_sorgusu)).scalar_one()

    eposta_bulunanlar = (
        await db.execute(
            select(func.count(CrawlerSearchResult.id))
            .join(CrawlerSearchJob)
            .join(CrawlerCompany)
            .where(
                *kosullar,
                CrawlerCompany.email.is_not(None),
                CrawlerCompany.email != "",
            )
        )
    ).scalar_one()

    alt_sektor_eslesmeleri = (
        await db.execute(
            select(func.count(CrawlerSearchResult.id))
            .join(CrawlerSearchJob)
            .join(CrawlerCompany)
            .where(*kosullar, CrawlerSearchResult.sector_match == "sub")
        )
    ).scalar_one()

    filtre_satirlari = (
        await db.execute(
            select(CrawlerCompany.country, CrawlerSearchResult.platform)
            .join(CrawlerSearchResult)
            .join(CrawlerSearchJob)
            .where(CrawlerSearchJob.batch_id == grup.id)
            .distinct()
        )
    ).all()

    istatistikler = {
        "total": toplam,
        "countries": ulke_sayisi,
        "emails_found": eposta_bulunanlar,
        "verified_emails": 0,
        "sub_sector_matches": alt_sektor_eslesmeleri,
        "country_options": sorted({row.country for row in filtre_satirlari if row.country}),
        "platform_options": sorted({row.platform for row in filtre_satirlari if row.platform}),
    }

    return ResultsPage(
        page=page,
        page_size=page_size,
        total=toplam,
        pages=max(1, math.ceil(toplam / page_size)),
        stats=istatistikler,
        results=sonuclar,
    )


@router.post("/search-batches/{batch_id}/exports", response_model=ExportCreated, status_code=202)
async def disa_aktarma_olustur(
    batch_id: str,
    body: ExportRequest = Body(default_factory=ExportRequest),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    grup = await _kullaniciya_ait_grup(db, batch_id, current_user["sub"])
    aktarma = SearchExport(
        batch_id=grup.id,
        user_id=current_user["sub"],
        filters=body.model_dump(exclude_none=True),
    )
    db.add(aktarma)
    await db.commit()
    await db.refresh(aktarma)
    enqueue_export(aktarma.id)
    return ExportCreated(id=aktarma.id, status=aktarma.status)


@router.get("/exports/{export_id}", response_model=ExportStatus)
async def disa_aktarma_durumu(
    export_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    sonuc = await db.execute(
        select(SearchExport).where(
            SearchExport.id == export_id,
            SearchExport.user_id == current_user["sub"],
        )
    )
    aktarma = sonuc.scalar_one_or_none()
    if not aktarma:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")

    url = f"/api/exports/{aktarma.id}/download" if aktarma.status == "COMPLETED" else None
    return ExportStatus(
        id=aktarma.id,
        status=aktarma.status,
        download_url=url,
        error_message=PublicErrorService.message(None, bool(aktarma.error_message)),
    )


@router.get("/exports/{export_id}/download")
async def disa_aktarma_indir(
    export_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    sonuc = await db.execute(
        select(SearchExport).where(
            SearchExport.id == export_id,
            SearchExport.user_id == current_user["sub"],
        )
    )
    aktarma = sonuc.scalar_one_or_none()
    if not aktarma or aktarma.status != "COMPLETED" or not aktarma.file_url:
        raise HTTPException(status_code=404, detail="Rapor hazır değil")

    if aktarma.file_url.startswith("storage:"):
        if not admin_supabase:
            raise HTTPException(status_code=503, detail="Storage yapılandırılmamış")
        try:
            kova_adi = getattr(settings, "reports_bucket", "reports")
            imzali = admin_supabase.storage.from_(kova_adi).create_signed_url(
                aktarma.file_url.removeprefix("storage:"), 60
            )
            imzali_url = imzali.get("signedURL") or imzali.get("signedUrl") or imzali.get("signed_url")
            if isinstance(imzali_url, str) and imzali_url:
                return RedirectResponse(imzali_url)
        except Exception:
            pass
        raise HTTPException(status_code=503, detail="Rapor indirme bağlantısı üretilemedi")

    if not os.path.isfile(aktarma.file_url):
        raise HTTPException(status_code=410, detail="Rapor dosyası artık mevcut değil")

    return FileResponse(
        aktarma.file_url,
        filename=f"pusula-{aktarma.batch_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


create_batch = arama_grubu_olustur
start_batch = arama_grubunu_baslat
batch_status = arama_grubu_durumu
batch_results = arama_grubu_sonuclari
create_export = disa_aktarma_olustur
export_status = disa_aktarma_durumu
download_export = disa_aktarma_indir
