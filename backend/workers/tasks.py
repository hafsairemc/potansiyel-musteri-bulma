from datetime import datetime
from sqlalchemy import func

from core.database import SessionLocal
from models.crawler_model import CrawlerSearchJob, SearchBatch, SearchExport
from models.product_model import ProductModel
from services.excel_service import create_batch_export
from services.intelligence_service import (
    run_fair_analysis,
    run_rfq_search,
)
from services.visitor_service import VisitorService
from services.email_campaign_service import send_campaign
from services.demand_publication_service import publish_demand_post
from services.orchestrator_service import OrchestratorService


def _toplu_arama_durumunu_guncelle(db, batch_id: str | None) -> None:
    if not batch_id:
        return
    toplu_gorev = db.query(SearchBatch).filter(SearchBatch.id == batch_id).first()
    if not toplu_gorev:
        return
    satirlar = db.query(CrawlerSearchJob.status, func.count(CrawlerSearchJob.id)).filter(
        CrawlerSearchJob.batch_id == batch_id
    ).group_by(CrawlerSearchJob.status).all()
    sayilar = dict(satirlar)
    toplu_gorev.completed_jobs = sayilar.get("COMPLETED", 0) + sayilar.get("COMPLETED_WITH_ERRORS", 0)
    toplu_gorev.failed_jobs = sayilar.get("FAILED", 0) + sayilar.get("CANCELLED", 0)
    tamamlanan = toplu_gorev.completed_jobs + toplu_gorev.failed_jobs
    toplu_gorev.progress = int((tamamlanan / toplu_gorev.total_jobs) * 100) if toplu_gorev.total_jobs else 0
    if tamamlanan >= toplu_gorev.total_jobs:
        toplu_gorev.status = "COMPLETED_WITH_ERRORS" if toplu_gorev.failed_jobs else "COMPLETED"
    elif sayilar.get("RUNNING", 0):
        toplu_gorev.status = "RUNNING"
    db.commit()


_refresh_batch = _toplu_arama_durumunu_guncelle


def arama_gorevini_calistir(job_id: str) -> None:
    db = SessionLocal()
    gorev = db.query(CrawlerSearchJob).filter(CrawlerSearchJob.id == job_id).first()
    if not gorev:
        db.close()
        return
    if gorev.status in {"COMPLETED", "COMPLETED_WITH_ERRORS", "CANCELLED"}:
        db.close()
        return
    toplu_id = gorev.batch_id
    try:
        gorev.attempt_count += 1
        gorev.status = "RUNNING"
        gorev.progress = 5
        db.commit()
        urun = gorev.product
        if urun is None:
            raise RuntimeError("Arama görevinin ürünü bulunamadı")
        urun_verisi = {
            "product_name": urun.name_tr,
            "product_name_en": urun.name_en,
            "translations": [urun.name_de, urun.name_fr, urun.name_ru, urun.name_es, urun.name_ar],
            "hs_code": urun.hs_code,
            "description": urun.description,
            "search_profile": urun.search_profile or {},
            "sub_sectors": [oge.industry_name for oge in urun.industries],
            "competitors": [oge.brand_name for oge in urun.competitors],
        }
        db.close()
        OrchestratorService().run_job(job_id, urun_verisi)
        db = SessionLocal()
        gorev = db.query(CrawlerSearchJob).filter(CrawlerSearchJob.id == job_id).first()
        if gorev and gorev.status in {"COMPLETED", "COMPLETED_WITH_ERRORS"}:
            gorev.progress = 100
            gorev.end_time = datetime.utcnow()
            db.commit()
    except Exception as exc:
        db.rollback()
        gorev = db.query(CrawlerSearchJob).filter(CrawlerSearchJob.id == job_id).first()
        if gorev:
            gorev.status = "FAILED"
            gorev.error_code = "WORKER_ERROR"
            gorev.error_message = str(exc)[:2000]
            gorev.end_time = datetime.utcnow()
            db.commit()
        raise
    finally:
        _toplu_arama_durumunu_guncelle(db, toplu_id)
        db.close()


run_search_job = arama_gorevini_calistir


def disa_aktarim_olustur(export_id: str) -> None:
    create_batch_export(export_id)


build_export = disa_aktarim_olustur


def rfq_gorevini_calistir(search_id: str) -> None:
    run_rfq_search(search_id)


run_rfq_task = rfq_gorevini_calistir



def fuar_gorevini_calistir(analysis_id: str) -> None:
    run_fair_analysis(analysis_id)


run_fair_task = fuar_gorevini_calistir


def suresi_dolan_ziyaretcileri_temizle() -> int:
    return VisitorService.delete_expired()


cleanup_expired_visitors = suresi_dolan_ziyaretcileri_temizle


def eposta_kampanyasini_calistir(campaign_id: str) -> None:
    send_campaign(campaign_id)


run_email_campaign_task = eposta_kampanyasini_calistir


def talep_ilanini_calistir(post_id: str) -> None:
    publish_demand_post(post_id)


run_demand_post_task = talep_ilanini_calistir


try:
    from workers.celery_app import celery_app
    celery_app.task(name="pusula.run_search_job", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)(arama_gorevini_calistir)
    celery_app.task(name="pusula.build_export", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)(disa_aktarim_olustur)
    celery_app.task(name="pusula.run_rfq_search", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)(rfq_gorevini_calistir)
    celery_app.task(name="pusula.run_fair_analysis", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)(fuar_gorevini_calistir)
    celery_app.task(name="pusula.cleanup_expired_visitors")(suresi_dolan_ziyaretcileri_temizle)
    celery_app.task(name="pusula.run_email_campaign")(eposta_kampanyasini_calistir)
    celery_app.task(name="pusula.run_demand_post")(talep_ilanini_calistir)
except ImportError:
    pass
