import os
import logging
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from core.database import SessionLocal
from core.interfaces import SearchQuery
from models.intelligence_model import (
    FairAnalysis, FairEntry,
    RFQOpportunity, RFQSearch,
)
from models.product_model import ProductModel
from services.crawler.providers.serper_provider_sync import SerperProviderSync
from services.ai.keyword_builder_service_sync import B2B_PLATFORMS
from services.db import admin_supabase
from core.config import settings
from services.public_url_service import safe_public_url

logger = logging.getLogger(__name__)


def erisim_durumu(text: str, url: str = "") -> str:
    deger = f"{text} {url}".lower()
    if any(x in deger for x in ("captcha", "verify you are human", "robot check")):
        return "captcha_blocked"
    if any(x in deger for x in ("sign in", "log in", "login required", "üye girişi", "giriş yap")):
        return "login_required"
    return "public"


access_status = erisim_durumu


def _kamusal_url_mi(url: str) -> bool:
    ayristirilmis = urlparse(url)
    return ayristirilmis.scheme in {"http", "https"} and bool(ayristirilmis.netloc)


_public_url = _kamusal_url_mi


def _guvenli_kamusal_url(value: str) -> str | None:
    return safe_public_url(value)


_safe_public_url = _guvenli_kamusal_url


def kamusal_websitesi_incele(value: str) -> tuple[str, str]:
    url = _guvenli_kamusal_url(value)
    if not url:
        return "enrichment_blocked", ""
    basliklar = {"User-Agent": "PusulaResearchBot/1.0"}
    try:
        with httpx.Client(headers=basliklar, timeout=5, follow_redirects=False) as istemci:
            robots_url = urljoin(url, "/robots.txt")
            robots_yaniti = istemci.get(robots_url)
            if robots_yaniti.status_code == 200:
                ayristirici = RobotFileParser()
                ayristirici.set_url(robots_url)
                ayristirici.parse(robots_yaniti.text.splitlines())
                if not ayristirici.can_fetch(basliklar["User-Agent"], url):
                    return "robots_blocked", ""
            yanit = istemci.get(url)
            if yanit.status_code in {401, 403}:
                return "login_required", ""
            if yanit.status_code >= 300:
                return "enrichment_blocked", ""
            durum = erisim_durumu(yanit.text, url)
            if durum != "public":
                return durum, ""
            corba = BeautifulSoup(yanit.text, "html.parser")
            for etiket in corba(["script", "style", "noscript", "svg"]):
                etiket.decompose()
            return "public", " ".join(corba.get_text(" ", strip=True).split())[:3000]
    except httpx.HTTPError:
        return "enrichment_blocked", ""


inspect_public_website = kamusal_websitesi_incele


def _ilk_eslesme(pattern: str, text: str) -> str | None:
    eslesme = re.search(pattern, text, flags=re.IGNORECASE)
    return eslesme.group(0).strip() if eslesme else None


_first_match = _ilk_eslesme


def urun_terimleri(product: ProductModel) -> list[str]:
    profil = product.search_profile or {}
    degerler = [product.name_tr, product.name_en, *(profil.get("aliases_tr") or []), *(profil.get("aliases_en") or [])]
    return list(dict.fromkeys(str(v).strip() for v in degerler if v and str(v).strip()))[:8]


product_terms = urun_terimleri


def _platform_adi(url: str) -> str:
    sunucu = urlparse(url).netloc.lower().removeprefix("www.")
    return sunucu.split(".")[0].title() if sunucu else "Web"


_platform = _platform_adi


def rfq_aramasini_calistir(search_id: str) -> None:
    db = SessionLocal()
    arama = db.query(RFQSearch).filter(RFQSearch.id == search_id).first()
    if not arama:
        db.close()
        return

    try:
        arama.status = "RUNNING"
        arama.progress = 10
        db.commit()

        urun = db.query(ProductModel).filter(ProductModel.id == arama.product_id).first()
        terimler = urun_terimleri(urun)
        tirnakli = " OR ".join(f'"{terim}"' for terim in terimler[:5])
        platform_gruplari = [B2B_PLATFORMS[indeks:indeks + 6] for indeks in range(0, len(B2B_PLATFORMS), 6)]
        platform_sorgulari = []
        for grup in platform_gruplari:
            siteler = " OR ".join(f"site:{oge['domain']}" for oge in grup)
            platform_sorgulari.append(f"({tirnakli}) ({siteler}) (RFQ OR buyer)")

        sorgular = [
            f'({tirnakli}) (RFQ OR "request for quotation" OR "buying lead") "{arama.target_country}"',
            f'({tirnakli}) ("purchase requirement" OR "buyer request" OR "teklif talebi") "{arama.target_country}"',
            *platform_sorgulari,
        ]
        if arama.date_from:
            tarih_filtresi = arama.date_from.strftime("%Y-%m-%d")
            sorgular = [f"{sorgu} after:{tarih_filtresi}" for sorgu in sorgular]

        saglayici = SerperProviderSync()
        gorulenler = set()
        konum = 0

        for sorgu in sorgular:
            for satir in saglayici.search(SearchQuery(query_text=sorgu, target_country=arama.target_country, search_engine="Google", query_type="RFQ")):
                if satir.url in gorulenler or not _kamusal_url_mi(satir.url):
                    continue
                gorulenler.add(satir.url)
                metin = f"{satir.title} {satir.snippet}".lower()
                eslesenler = [terim for terim in terimler if terim.lower() in metin]
                rfq_eslesmeleri = [x for x in ("rfq", "request for quotation", "buying lead", "purchase requirement", "buyer request", "teklif talebi") if x in metin]
                if not eslesenler or not rfq_eslesmeleri:
                    continue

                konum += 1
                ilgi_skoru = min(100, 45 + len(eslesenler) * 12 + len(rfq_eslesmeleri) * 8)
                miktar = _ilk_eslesme(r"\b\d[\d.,]*\s*(?:kg|ton|tons|adet|pieces|pcs|units)\b", metin)
                son_tarih = _ilk_eslesme(r"\b(?:20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]20\d{2})\b", metin)
                guncellik = 80 if son_tarih else 50

                db.add(RFQOpportunity(
                    rfq_search_id=arama.id,
                    title=(satir.title or "Açık talep")[:500],
                    buyer_name=_platform_adi(satir.url),
                    country=arama.target_country,
                    quantity=miktar,
                    deadline=son_tarih,
                    description=(satir.snippet or "")[:3000],
                    platform=_platform_adi(satir.url),
                    source_url=satir.url,
                    access_status=erisim_durumu(satir.snippet or "", satir.url),
                    relevance_score=ilgi_skoru,
                    freshness_score=guncellik,
                    confidence_score=min(95, ilgi_skoru),
                    match_reason=f"Ürün: {', '.join(eslesenler[:3])}; talep sinyali: {', '.join(rfq_eslesmeleri[:2])}",
                ))
                if konum >= 25:
                    break
            if konum >= 25:
                break

        arama.status = "COMPLETED"
        arama.progress = 100
        db.commit()
    except Exception as exc:
        db.rollback()
        arama = db.query(RFQSearch).filter(RFQSearch.id == search_id).first()
        if arama:
            arama.status = "FAILED"
            arama.error_code = "RFQ_PROVIDER_ERROR"
            arama.error_message = str(exc)[:1500]
            db.commit()
    finally:
        db.close()


run_rfq_search = rfq_aramasini_calistir


def fuar_dosyasini_oku(path: str) -> pd.DataFrame:
    if Path(path).suffix.lower() != ".csv":
        return pd.read_excel(path)
    for kodlama in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
        try:
            return pd.read_csv(path, encoding=kodlama, sep=None, engine="python")
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV karakter kodlaması desteklenmiyor")


read_fair_file = fuar_dosyasini_oku


def _fuar_dosyasini_indir(analysis: FairAnalysis) -> tuple[str, bool]:
    if not analysis.file_path.startswith("storage:"):
        return analysis.file_path, False
    if not admin_supabase:
        raise RuntimeError("Supabase Storage yapılandırılmamış")

    uzanti = Path(analysis.filename).suffix.lower()
    yerel_yol = os.path.join(tempfile.gettempdir(), f"fair-worker-{analysis.id}{uzanti}")
    icerik = admin_supabase.storage.from_(settings.reports_bucket).download(
        analysis.file_path.removeprefix("storage:")
    )
    with open(yerel_yol, "wb") as dosya:
        dosya.write(icerik)
    return yerel_yol, True


_download_fair_file = _fuar_dosyasini_indir


def fuar_analizini_calistir(analysis_id: str) -> None:
    db = SessionLocal()
    yerel_yol = ""
    sonradan_sil = False
    analiz = db.query(FairAnalysis).filter(FairAnalysis.id == analysis_id).first()
    if not analiz:
        db.close()
        return

    try:
        analiz.status = "RUNNING"
        analiz.progress = 10
        db.commit()

        urun = db.query(ProductModel).filter(ProductModel.id == analiz.product_id).first()
        terimler = urun_terimleri(urun)
        yerel_yol, sonradan_sil = _fuar_dosyasini_indir(analiz)
        tablo = fuar_dosyasini_oku(yerel_yol).fillna("")

        analiz.total_rows = len(tablo)
        analiz.processed_rows = 0
        analiz.duplicate_rows = 0
        db.commit()

        esleme = analiz.column_mapping or {}
        firma_sutunu = esleme["company_name"]
        gorulenler = set()

        try:
            satir_limiti = max(1, min(int(os.getenv("FAIR_MAX_ROWS", "1000")), 10000))
        except ValueError:
            satir_limiti = 1000

        sinirli_tablo = tablo.head(satir_limiti)
        for islenen, (indeks, satir) in enumerate(sinirli_tablo.iterrows(), 1):
            firma = str(satir.get(firma_sutunu, "")).strip()
            if not firma or firma.lower() in gorulenler:
                if firma and firma.lower() in gorulenler:
                    analiz.duplicate_rows += 1
                continue

            gorulenler.add(firma.lower())
            degerler = {anahtar: str(satir.get(sutun, "")).strip() for anahtar, sutun in esleme.items() if sutun}
            web_sitesi = degerler.get("website") or None
            zenginlestirme_durumu = erisim_durumu(degerler.get("description", ""), web_sitesi or "")
            zenginlestirme_metni = ""
            zenginlestirme_limiti = max(0, min(int(os.getenv("FAIR_ENRICH_LIMIT", "25")), 100))

            if web_sitesi and islenen <= zenginlestirme_limiti:
                zenginlestirme_durumu, zenginlestirme_metni = kamusal_websitesi_incele(web_sitesi)

            metin = f"{' '.join(degerler.values())} {zenginlestirme_metni}".lower()
            eslesenler = [terim for terim in terimler if terim.lower() in metin]
            alici_eslesmeleri = [x for x in ("import", "ithalat", "wholesale", "toptan", "distributor", "distribütör", "buyer", "satın alma") if x in metin]

            ilgi_skoru = min(100, len(eslesenler) * 35)
            alici_skoru = min(100, len(alici_eslesmeleri) * 25)
            siniflandirma = "high_potential" if ilgi_skoru >= 60 else ("review" if ilgi_skoru >= 30 or alici_skoru >= 25 else "incompatible")

            db.add(FairEntry(
                fair_analysis_id=analiz.id,
                row_number=int(indeks) + 2,
                company_name=firma,
                website=web_sitesi,
                country=degerler.get("country"),
                city=degerler.get("city"),
                sector=degerler.get("sector"),
                description=degerler.get("description"),
                email=degerler.get("email"),
                phone=degerler.get("phone"),
                access_status=zenginlestirme_durumu,
                relevance_score=ilgi_skoru,
                buyer_score=alici_skoru,
                classification=siniflandirma,
                matched_terms=eslesenler,
                match_reason=(f"Eşleşen ürün terimleri: {', '.join(eslesenler)}" if eslesenler else "Doğrudan ürün eşleşmesi bulunamadı"),
                original_data={str(k): str(v) for k, v in satir.to_dict().items()},
            ))

            if islenen % 50 == 0:
                analiz.processed_rows = islenen
                analiz.progress = min(95, 10 + int(islenen / max(1, len(sinirli_tablo)) * 85))
                db.commit()

        analiz.processed_rows = len(sinirli_tablo)
        analiz.progress = 100
        if len(tablo) > satir_limiti:
            analiz.status = "COMPLETED_WITH_ERRORS"
            analiz.error_code = "ROW_LIMIT_APPLIED"
            analiz.error_message = f"{len(tablo)} satırın ilk {satir_limiti} satırı analiz edildi"
        else:
            analiz.status = "COMPLETED"
        db.commit()

        if analiz.file_path.startswith("storage:") and admin_supabase:
            nesne_adi = analiz.file_path.removeprefix("storage:")
            try:
                admin_supabase.storage.from_(settings.reports_bucket).remove([nesne_adi])
                analiz.file_path = "deleted:retention-complete"
                db.commit()
            except Exception as exc:
                logger.warning("Fuar kaynak dosyası silinemedi: %s", exc)
    except Exception as exc:
        db.rollback()
        analiz = db.query(FairAnalysis).filter(FairAnalysis.id == analysis_id).first()
        if analiz:
            analiz.status = "FAILED"
            analiz.error_code = "FAIR_FILE_ERROR"
            analiz.error_message = str(exc)[:1500]
            db.commit()
    finally:
        if sonradan_sil and yerel_yol and os.path.isfile(yerel_yol):
            os.remove(yerel_yol)
        db.close()


run_fair_analysis = fuar_analizini_calistir


def satirlari_disa_aktar(rows: list[dict], prefix: str) -> str:
    dosya_yolu = os.path.join(tempfile.gettempdir(), f"{prefix}.xlsx")
    guvenli_satirlar = []
    for satir in rows:
        guvenli_satirlar.append({
            anahtar: f"'{deger}" if isinstance(deger, str) and deger.startswith(("=", "+", "-", "@")) else deger
            for anahtar, deger in satir.items()
        })
    pd.DataFrame(guvenli_satirlar).to_excel(dosya_yolu, index=False)
    return dosya_yolu


export_rows = satirlari_disa_aktar
