from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_db
from core.rate_limit import limiter
from core.security import get_current_user
from models.crawler_model import CrawlerCompany, CrawlerSearchResult
from models.schemas import SearchJobCreate, SearchJobResponse
from services.search_job_service import SearchJobService
from services.task_queue import enqueue_job

router = APIRouter(prefix="/search-jobs", tags=["Search Jobs"])


@router.post("/", response_model=SearchJobResponse)
@limiter.limit("30/minute")
async def arama_gorevi_olustur(
    request: Request,
    job_in: SearchJobCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    servis = SearchJobService(db)
    kullanici_id = str(current_user["sub"])
    return await servis.create_job(job_in, user_id=kullanici_id)


@router.get("/", response_model=list[SearchJobResponse])
@limiter.limit("60/minute")
async def arama_gorevlerini_getir(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    servis = SearchJobService(db)
    return await servis.get_all_jobs(skip=skip, limit=limit, user_id=current_user["sub"])


@router.get("/{job_id}", response_model=SearchJobResponse)
@limiter.limit("60/minute")
async def arama_gorevi_getir(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    servis = SearchJobService(db)
    gorev = await servis.get_job(job_id, user_id=current_user["sub"])
    if not gorev:
        raise HTTPException(status_code=404, detail="SearchJob bulunamadı")
    return gorev


@router.post("/{job_id}/start")
@limiter.limit("10/minute")
async def arama_gorevini_baslat(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    servis = SearchJobService(db)
    try:
        gorev = await servis.start_job(job_id, user_id=current_user["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        enqueue_job(gorev.id)
    except Exception as exc:
        await servis.mark_pending(gorev)
        raise HTTPException(status_code=503, detail="Arama görevi kuyruğa alınamadı") from exc

    return {"message": "Arama başlatıldı", "job_id": gorev.id, "status": gorev.status}


@router.get("/{job_id}/status")
@limiter.limit("120/minute")
async def arama_gorevi_durumu_al(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    servis = SearchJobService(db)
    gorev = await servis.get_job(job_id, user_id=current_user["sub"])
    if not gorev:
        raise HTTPException(status_code=404, detail="SearchJob bulunamadı")
    return {"job_id": gorev.id, "status": gorev.status, "report_url": gorev.report_url}


@router.get("/{job_id}/results")
@limiter.limit("60/minute")
async def arama_gorevi_sonuclari_al(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    servis = SearchJobService(db)
    gorev = await servis.get_job(job_id, user_id=current_user["sub"])
    if not gorev:
        raise HTTPException(status_code=404, detail="SearchJob bulunamadı")

    sorgu = (
        select(CrawlerSearchResult, CrawlerCompany)
        .join(CrawlerCompany, CrawlerCompany.id == CrawlerSearchResult.company_id)
        .where(CrawlerSearchResult.search_job_id == job_id)
        .order_by(CrawlerSearchResult.position)
    )
    sonuc = await db.execute(sorgu)
    firmalar = []

    for arama_sonucu, firma in sonuc.all():
        firmalar.append({
            "company_name": firma.name or "Bilinmiyor",
            "country": firma.country or "—",
            "email": firma.email or "",
            "email_verified": firma.email_status == "verified",
            "email_status": firma.email_status,
            "email_source_url": firma.email_source_url,
            "phone": firma.phone or "",
            "address": firma.address or "",
            "website": arama_sonucu.source_url or "",
            "source": arama_sonucu.source,
            "sector_match": arama_sonucu.sector_match,
        })

    istatistikler = {
        "total": len(firmalar),
        "countries": len(set(f["country"] for f in firmalar)),
        "emails_found": sum(1 for f in firmalar if f["email"]),
        "verified_emails": sum(1 for f in firmalar if f["email_verified"]),
        "sub_sector_matches": 0,
    }

    return {"stats": istatistikler, "results": firmalar}


create_search_job = arama_gorevi_olustur
get_search_jobs = arama_gorevlerini_getir
get_search_job = arama_gorevi_getir
start_search_job = arama_gorevini_baslat
get_search_job_status = arama_gorevi_durumu_al
get_search_job_results = arama_gorevi_sonuclari_al
