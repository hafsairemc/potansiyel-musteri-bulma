import os
import logging
from typing import Any
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.crawler_model import CrawlerSearchJob, CrawlerSearchResult, CrawlerCompany, CrawlerCompanyWebsite
from services.ai.keyword_builder_service_sync import KeywordBuilderServiceSync
from services.crawler.providers.serper_provider_sync import SerperProviderSync
from services.crawler.providers.yandex_provider_sync import YandexProviderSync, YandexProviderError
from services.crawler.providers.serper_maps_provider_sync import SerperMapsProviderSync, SerperMapsError
from services.crawler.domain_normalizer import DomainNormalizer
from services.company_analyzer_service import CompanyAnalyzerService
from models.schemas import JobStatus
from services.ai.keyword_builder_service_sync import B2B_PLATFORMS
from services.map_search_service import MapSearchService
from core.interfaces import SearchResult
from services.site_enrichment_service import SiteEnrichmentService

logger = logging.getLogger(__name__)


class OrkestraServisi:
    def __init__(self):
        self.keyword_builder = KeywordBuilderServiceSync()
        self.search_engine = SerperProviderSync()
        self.yandex_engine = YandexProviderSync()
        self.maps_engine = SerperMapsProviderSync()
        self.fallback_maps_engine = MapSearchService()
        self.domain_normalizer = DomainNormalizer()
        self.site_scraper = SiteEnrichmentService()
        self.analyzer = CompanyAnalyzerService()

    def gorevi_calistir(self, job_id: str, product_data: dict[str, Any]):
        db: Session = SessionLocal()
        try:
            islem = db.query(CrawlerSearchJob).filter(CrawlerSearchJob.id == job_id).first()
            if not islem:
                logger.warning("Arama görevi bulunamadı: %s", job_id)
                return

            islem.status = JobStatus.RUNNING.value
            db.commit()
            logger.info("Arama görevi başlatıldı: %s", job_id)

            arama_baglami = {
                "target_country": islem.target_country or "Global",
                "search_engine": islem.search_engine or "Google",
                "source": islem.source or "search_engine",
            }

            if islem.source == "google_maps":
                self._harita_aramasini_calistir(db, islem, product_data)
                return

            sorgular = self.keyword_builder.build_queries(product_data, arama_baglami)
            logger.info("%s arama sorgusu oluşturuldu", len(sorgular))

            tum_arama_sonuclari = []
            sorgu_hatalari = []
            azami_sorgu = max(1, min(int(os.getenv("CRAWLER_MAX_QUERIES", "12")), 30))

            for sorgu in sorgular[:azami_sorgu]:
                try:
                    saglayici = self.yandex_engine if islem.source == "yandex_web" else self.search_engine
                    sonuclar = saglayici.search(sorgu, max_pages=1)
                    tum_arama_sonuclari.extend(sonuclar)
                except Exception as exc:
                    logger.warning("Sorgu hatası (%s): %s", sorgu.query_text, exc)
                    if isinstance(exc, YandexProviderError) or str(exc).startswith("SERPER_"):
                        raise
                    sorgu_hatalari.append(str(exc))

            benzersiz_sonuclar = self.domain_normalizer.filter_duplicates(tum_arama_sonuclari)
            azami_sonuc = max(5, min(int(os.getenv("CRAWLER_MAX_RESULTS_PER_JOB", "20")), 50))
            benzersiz_sonuclar = benzersiz_sonuclar[:azami_sonuc]
            logger.info("%s benzersiz şirket web sitesi bulundu", len(benzersiz_sonuclar))

            islem.total_companies = len(benzersiz_sonuclar)
            islem.progress = 45
            db.commit()

            if not benzersiz_sonuclar:
                if sorgu_hatalari:
                    raise RuntimeError("Arama sağlayıcısı sorguları tamamlayamadı")
                islem.status = JobStatus.COMPLETED.value
                islem.progress = 100
                db.commit()
                return

            basari_sayisi = 0
            for sira, arama_sonucu in enumerate(benzersiz_sonuclar):
                try:
                    kazinan = self.site_scraper.scrape(arama_sonucu.url)
                    analiz = self.analyzer.analyze_company(
                        company_name=kazinan.get("company_name", arama_sonucu.title),
                        product_name=product_data.get("product_name", ""),
                        about_us_text=kazinan.get("about_us_text") or arama_sonucu.snippet or "",
                        contact_text=kazinan.get("contact_text", ""),
                        search_profile=product_data.get("search_profile") or {},
                        source=islem.source,
                    )
                    if not analiz.get("is_relevant"):
                        continue

                    sirket_id = self._kesiti_kaydet(db, islem, arama_sonucu, sira + 1)
                    self._sirketi_zenginlestir(db, sirket_id, kazinan, analiz, arama_sonucu.url)
                    self._sonucu_zenginlestir(
                        db, job_id, sirket_id, arama_sonucu.query or islem.search_query,
                        analiz, islem.source,
                        self._urlden_platform_bul(arama_sonucu.url) if islem.source == "b2b_platform" else arama_sonucu.platform,
                    )
                    basari_sayisi += 1
                except Exception as exc:
                    db.rollback()
                    logger.warning("Şirket işleme hatası (%s): %s", arama_sonucu.url, exc)

            islem.status = self._tamamlanma_durumu(sorgu_hatalari, len(benzersiz_sonuclar) - basari_sayisi)
            islem.successful_companies = basari_sayisi
            islem.failed_companies = max(0, len(benzersiz_sonuclar) - basari_sayisi)
            if sorgu_hatalari:
                islem.error_code = "PARTIAL_PROVIDER_ERRORS"
                islem.error_message = f"{len(sorgu_hatalari)} sorgu tamamlanamadı"
            islem.progress = 100
            db.commit()
            logger.info("Görev tamamlandı, %s şirket kaydedildi", basari_sayisi)

        except Exception as exc:
            logger.exception("Görev genel hatası (%s): %s", job_id, exc)
            islem = db.query(CrawlerSearchJob).filter(CrawlerSearchJob.id == job_id).first()
            if islem:
                islem.status = JobStatus.FAILED.value
                islem.error_code = getattr(exc, "code", None) or str(exc).split(":", 1)[0][:100] or "PROVIDER_ERROR"
                islem.error_message = str(exc)[:2000]
                db.commit()
            raise
        finally:
            db.close()

    run_job = gorevi_calistir

    def _kesiti_kaydet(self, db: Session, job: CrawlerSearchJob, search_result, position: int) -> str:
        mevcut_sonuc = db.query(CrawlerSearchResult).filter(
            CrawlerSearchResult.search_job_id == job.id,
            CrawlerSearchResult.source_url == search_result.url,
        ).first()
        if mevcut_sonuc:
            mevcut_sonuc.position = min(mevcut_sonuc.position or position, position)
            db.commit()
            return mevcut_sonuc.company_id

        alan_adi = self.domain_normalizer.normalize_domain(search_result.url)
        web_sitesi = None
        if job.source != "google_maps" and alan_adi:
            web_sitesi = db.query(CrawlerCompanyWebsite).filter(CrawlerCompanyWebsite.domain == alan_adi).first()

        sirket = web_sitesi.company if web_sitesi else None
        if not sirket:
            sirket = CrawlerCompany(
                name=search_result.title or "Bilinmiyor",
                about_us_text=(search_result.snippet or "")[:500] or None,
                phone=search_result.phone,
                email=search_result.email,
                email_status="public_source" if search_result.email else None,
                email_source_url=search_result.url if search_result.email else None,
                address=search_result.address,
                country=search_result.country or job.target_country,
                city=search_result.city,
            )
            db.add(sirket)
            db.flush()
            if job.source != "google_maps" and alan_adi:
                db.add(CrawlerCompanyWebsite(company_id=sirket.id, url=search_result.url, domain=alan_adi, status="FOUND"))

        sr = CrawlerSearchResult(
            search_job_id=job.id,
            company_id=sirket.id,
            source_url=search_result.url,
            position=position,
            source=job.source,
            platform=(self._urlden_platform_bul(search_result.url) if job.source == "b2b_platform" else search_result.platform),
            search_query=search_result.query or job.search_query,
        )
        db.add(sr)
        db.commit()
        return sirket.id

    _save_snippet = _kesiti_kaydet

    def _sirketi_zenginlestir(self, db: Session, company_id: str, scraped: dict, analysis: dict, source_url: str):
        sirket = db.query(CrawlerCompany).filter(CrawlerCompany.id == company_id).first()
        if not sirket:
            return
        if analysis.get("company_name") or scraped.get("company_name"):
            sirket.name = analysis.get("company_name") or scraped.get("company_name")
        if analysis.get("email") or scraped.get("email"):
            sirket.email = analysis.get("email") or scraped.get("email")
            sirket.email_status = "public_source"
            sirket.email_source_url = source_url
        if analysis.get("phone") or scraped.get("phone"):
            sirket.phone = analysis.get("phone") or scraped.get("phone")
        if scraped.get("address"):
            sirket.address = scraped["address"]
        if analysis.get("country") or scraped.get("country"):
            sirket.country = analysis.get("country") or scraped.get("country")
        if scraped.get("about_us_text"):
            sirket.about_us_text = scraped["about_us_text"][:2000]
        if scraped.get("contact_text"):
            sirket.contact_text = scraped["contact_text"][:2000]
        db.commit()

    _enrich_company = _sirketi_zenginlestir

    def _sonucu_zenginlestir(self, db: Session, job_id: str, company_id: str, query: str, analysis: dict, source: str, platform: str | None = None):
        sonuc = db.query(CrawlerSearchResult).filter(
            CrawlerSearchResult.search_job_id == job_id,
            CrawlerSearchResult.company_id == company_id,
        ).first()
        if not sonuc:
            return
        sonuc.source = source or "search_engine"
        sonuc.platform = platform
        sonuc.search_query = query
        sonuc.customer_type = analysis.get("customer_type") or "sector_candidate"
        sonuc.score = int(analysis.get("potential_customer_score") or 0)
        sonuc.relevance_score = int(analysis.get("relevance_score") or 0)
        sonuc.buyer_score = int(analysis.get("buyer_score") or 0)
        sonuc.matched_terms = analysis.get("matched_terms") or []
        sonuc.category_path = analysis.get("category_path") or None
        sonuc.confidence_score = int(analysis.get("confidence_score") or 0)
        sonuc.match_reason = analysis.get("match_reason")
        sonuc.sector_match = "main" if analysis.get("sells_product") else "sub"
        db.commit()

    _enrich_result = _sonucu_zenginlestir

    def _harita_aramasini_calistir(self, db: Session, job: CrawlerSearchJob, product_data: dict[str, Any]):
        try:
            satirlar = self.maps_engine.search(product_data.get("product_name", ""), job.target_country or "Türkiye")
        except SerperMapsError as exc:
            logger.warning("Serper Maps kullanılamadı, ücretsiz harita kaynağı deneniyor: %s", exc)
            satirlar = []

        if not satirlar:
            yedek_satirlar = self.fallback_maps_engine.search(product_data, job.target_country or "Türkiye")
            satirlar = [SearchResult(
                url=satir.get("website") or "",
                title=satir.get("name") or "Bilinmiyor",
                snippet=satir.get("address") or "",
                platform="HERE" if satir.get("source") == "here" else "OpenStreetMap",
                phone=satir.get("phone"),
                email=satir.get("email"),
                address=satir.get("address"),
                country=satir.get("country"),
                query=product_data.get("product_name", ""),
            ) for satir in yedek_satirlar if satir.get("website")]

        gorulenler: set[str] = set()
        benzersiz_satirlar = []
        for satir in satirlar:
            if satir.url in gorulenler:
                continue
            gorulenler.add(satir.url)
            benzersiz_satirlar.append(satir)

        satirlar = benzersiz_satirlar
        for sira, satir in enumerate(satirlar, 1):
            birlesik = " ".join(filter(None, [satir.title, satir.snippet, satir.address]))
            analiz = self.analyzer.analyze_company(
                satir.title, product_data.get("product_name", ""), birlesik, "",
                product_data.get("search_profile") or {}, "google_maps",
            )
            if not analiz.get("is_relevant"):
                continue
            sirket_id = self._kesiti_kaydet(db, job, satir, sira)
            self._sonucu_zenginlestir(db, job.id, sirket_id, satir.query, analiz, "google_maps", "Google Maps")

        kaydedilen_sayi = db.query(CrawlerSearchResult).filter(CrawlerSearchResult.search_job_id == job.id).count()
        job.total_companies = len(satirlar)
        job.successful_companies = kaydedilen_sayi
        job.failed_companies = max(0, len(satirlar) - kaydedilen_sayi)
        job.status = JobStatus.COMPLETED.value
        db.commit()

    _run_map_search = _harita_aramasini_calistir

    @staticmethod
    def _urlden_platform_bul(url: str) -> str | None:
        kucuk = (url or "").lower()
        for oge in B2B_PLATFORMS:
            if oge["domain"] in kucuk:
                return oge["label"]
        return "Yandex" if "yandex." in kucuk else "Google"

    _platform_from_url = _urlden_platform_bul

    @staticmethod
    def _tamamlanma_durumu(query_errors: list[str], failed_companies: int) -> str:
        if query_errors or failed_companies:
            return JobStatus.COMPLETED_WITH_ERRORS.value
        return JobStatus.COMPLETED.value

    _completion_status = _tamamlanma_durumu


OrchestratorService = OrkestraServisi


def orkestra_gorevini_senkron_calistir(job_id: str, product_data: dict[str, Any]):
    OrkestraServisi().gorevi_calistir(job_id, product_data)


run_orchestrator_task_sync = orkestra_gorevini_senkron_calistir
