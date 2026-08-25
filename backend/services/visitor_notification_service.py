import os
import httpx


class ZiyaretciBildirimServisi:
    def gonder(self, visitor: dict) -> bool:
        webhook_url = os.getenv("VISITOR_NOTIFICATION_WEBHOOK", "").strip()
        if not webhook_url:
            return False
        mesaj = {
            "event": "visitor_detected",
            "country": visitor.get("country"),
            "city": visitor.get("city"),
            "company_candidate": visitor.get("operator"),
            "detection_method": visitor.get("detection_method"),
            "confidence": visitor.get("confidence"),
        }
        try:
            yanit = httpx.post(webhook_url, json=mesaj, timeout=5)
            return yanit.is_success
        except httpx.HTTPError:
            return False

    send = gonder


VisitorNotificationService = ZiyaretciBildirimServisi
