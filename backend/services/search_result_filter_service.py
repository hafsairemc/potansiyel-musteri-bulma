from sqlalchemy import or_
from models.crawler_model import CrawlerCompany, CrawlerSearchJob, CrawlerSearchResult


def sonuc_kosullari(batch_id: str, filters: dict) -> list:
    kosullar = [CrawlerSearchJob.batch_id == batch_id]
    eslemeler = (
        ("country", CrawlerCompany.country),
        ("city", CrawlerCompany.city),
        ("source", CrawlerSearchResult.source),
        ("platform", CrawlerSearchResult.platform),
        ("customer_type", CrawlerSearchResult.customer_type),
        ("sector_match", CrawlerSearchResult.sector_match),
    )
    for anahtar, sutun in eslemeler:
        deger = filters.get(anahtar)
        if deger:
            kosullar.append(sutun == deger)

    kosullar.append(CrawlerSearchResult.score >= int(filters.get("min_score") or 0))
    kosullar.append(CrawlerSearchResult.relevance_score >= int(filters.get("min_relevance") or 0))

    sorgu_metni = str(filters.get("q") or "").strip()
    if sorgu_metni:
        kacirilmis = sorgu_metni.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        kalip = f"%{kacirilmis}%"
        kosullar.append(or_(
            CrawlerCompany.name.ilike(kalip, escape="\\"),
            CrawlerCompany.email.ilike(kalip, escape="\\"),
            CrawlerSearchResult.match_reason.ilike(kalip, escape="\\"),
        ))

    return kosullar


result_conditions = sonuc_kosullari
