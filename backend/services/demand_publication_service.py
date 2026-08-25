import os
from datetime import datetime
import httpx

from core.database import SessionLocal
from models.growth_model import DemandPost

PLATFORM_YAYINLAMA_SAYFALARI = {
    "TurkishExporter": "https://www.turkishexporter.com.tr/",
    "Europages": "https://www.europages.com/",
    "TradeKey": "https://www.tradekey.com/",
    "ECPlaza": "https://www.ecplaza.net/",
    "eWorldTrade": "https://www.eworldtrade.com/",
}

PLATFORM_PUBLISH_PAGES = PLATFORM_YAYINLAMA_SAYFALARI


def talep_ilanini_yayinla(post_id: str) -> None:
    db = SessionLocal()
    ilan = db.query(DemandPost).filter(DemandPost.id == post_id).first()
    if not ilan or ilan.status != "QUEUED":
        db.close()
        return

    ilan.status = "PUBLISHING"
    db.commit()

    webhook_url = os.getenv("B2B_PUBLISH_WEBHOOK_URL")
    webhook_token = os.getenv("B2B_PUBLISH_WEBHOOK_TOKEN")

    for hedef in ilan.targets:
        hedef.publication_url = PLATFORM_YAYINLAMA_SAYFALARI[hedef.platform]
        if not webhook_url:
            hedef.status = "MANUAL_REQUIRED"
            continue
        try:
            yanit = httpx.post(
                webhook_url,
                headers={"Authorization": f"Bearer {webhook_token}"} if webhook_token else {},
                json={
                    "platform": hedef.platform,
                    "title": ilan.title,
                    "description": ilan.description,
                    "quantity": ilan.quantity,
                    "target_country": ilan.target_country,
                    "deadline": ilan.deadline.isoformat() if ilan.deadline else None,
                },
                timeout=20,
            )
            yanit.raise_for_status()
            veri = yanit.json() if yanit.content else {}
            hedef.publication_url = veri.get("publication_url") or hedef.publication_url
            hedef.status = "PUBLISHED"
            hedef.published_at = datetime.utcnow()
        except Exception as exc:
            hedef.status = "FAILED"
            hedef.error_message = str(exc)[:1000]

    durumlar = {hedef.status for hedef in ilan.targets}
    if durumlar == {"PUBLISHED"}:
        ilan.status = "COMPLETED"
    elif "PUBLISHED" in durumlar or "MANUAL_REQUIRED" in durumlar:
        ilan.status = "COMPLETED_WITH_ACTIONS"
    else:
        ilan.status = "FAILED"

    db.commit()
    db.close()


publish_demand_post = talep_ilanini_yayinla
