import os
from datetime import datetime, timedelta

from services.visitor_notification_service import VisitorNotificationService
from services.visitor_service import VisitorService


class ZiyaretciOlayServisi:
    def __init__(self, storage=None, notifier=None):
        self.storage = storage or VisitorService
        self.notifier = notifier or VisitorNotificationService()

    def olayi_kaydet(self, data: dict) -> tuple[str | None, dict]:
        olay = dict(data)
        olay.setdefault(
            "retention_until",
            datetime.now() + timedelta(days=self._saklama_gun_sayisi()),
        )
        return self.storage.save_visitor_to_db(olay), olay

    save = olayi_kaydet

    def bildir(self, event: dict) -> bool:
        return self.notifier.send(event)

    notify = bildir

    @staticmethod
    def _saklama_gun_sayisi() -> int:
        try:
            return max(1, min(int(os.getenv("VISITOR_RETENTION_DAYS", "90")), 365))
        except ValueError:
            return 90

    _retention_days = _saklama_gun_sayisi


VisitorEventService = ZiyaretciOlayServisi
