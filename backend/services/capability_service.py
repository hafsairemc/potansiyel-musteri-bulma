import os
from services.search_source_service import SearchSourceService


class YetenekServisi:
    def __init__(self, environ=None):
        self.environ = os.environ if environ is None else environ

    def _yapilandirilmis_mi(self, *names: str) -> bool:
        return all(bool(self.environ.get(name, "").strip()) for name in names)

    _configured = _yapilandirilmis_mi

    def _madde(
        self,
        key: str,
        label: str,
        configured: bool,
        unavailable_text: str,
        ready_text: str = "Kullanıma hazır",
    ) -> dict:
        return {
            "key": key,
            "label": label,
            "status": "ready" if configured else "not_configured",
            "message": ready_text if configured else unavailable_text,
        }

    _item = _madde

    def listele(self) -> list[dict]:
        kaynaklar = SearchSourceService(self.environ)
        kuyruk_gerekli_mi = (
            self.environ.get("TASK_QUEUE_MODE", "celery").lower() == "celery"
        )
        kuyruk_hazir_mi = not kuyruk_gerekli_mi or self._yapilandirilmis_mi("REDIS_URL")
        google_hazir, google_mesaji = kaynaklar.status("google_web")
        harita_hazir, harita_mesaji = kaynaklar.status("google_maps")
        yandex_hazir, yandex_mesaji = kaynaklar.status("yandex_web")
        uzak_veritabani = self.environ.get("USE_REMOTE_DB", "false").lower() == "true"
        veritabani_hazir = not uzak_veritabani or self._yapilandirilmis_mi("DATABASE_URL")

        maddeler = [
            self._madde(
                "database",
                "Veritabanı",
                veritabani_hazir,
                "DATABASE_URL gerekli",
                "Supabase PostgreSQL" if uzak_veritabani else "Yerel SQLite",
            ),
            self._madde("google_web", "Google Web", google_hazir, google_mesaji),
            self._madde("google_maps", "Google Haritalar", harita_hazir, harita_mesaji),
            self._madde("yandex_web", "Yandex Web", yandex_hazir, yandex_mesaji),
            self._madde(
                "openai",
                "AI özellikleri",
                self._yapilandirilmis_mi("OPENAI_API_KEY"),
                "Yerleşik yardım ve sorgu şablonları kullanılacak",
            ),
            self._madde(
                "task_queue",
                "Arka plan görevleri",
                kuyruk_hazir_mi,
                "Redis bağlantısı gerekli",
            ),
            self._madde(
                "email_send",
                "E-posta gönderimi",
                self._yapilandirilmis_mi("SMTP_HOST", "SMTP_FROM_EMAIL"),
                "SMTP ayarları gerekli",
            ),
            self._madde(
                "email_delivery",
                "E-posta teslim takibi",
                self._yapilandirilmis_mi("EMAIL_EVENT_WEBHOOK_SECRET"),
                "İmzalı sağlayıcı webhook'u gerekli",
            ),
            self._madde(
                "email_replies",
                "E-posta yanıt ve bounce takibi",
                self._yapilandirilmis_mi("IMAP_HOST", "IMAP_USERNAME", "IMAP_PASSWORD"),
                "IMAP ayarları gerekli",
            ),
            self._madde(
                "demand_publish",
                "Otomatik talep yayınlama",
                self._yapilandirilmis_mi("B2B_PUBLISH_WEBHOOK_URL"),
                "Platform bağlantılarıyla manuel tamamlama kullanılacak",
            ),
        ]
        maddeler.append(
            {
                "key": "map_fallback",
                "label": "Ücretsiz harita yedeği",
                "status": "ready",
                "message": (
                    "OpenStreetMap/Overpass kullanıma hazır"
                    if not self._yapilandirilmis_mi("HERE_API_KEY")
                    else "OpenStreetMap ve HERE kullanıma hazır"
                ),
            }
        )
        return maddeler

    list = listele

    def ozet(self) -> dict:
        maddeler = self.listele()
        return {
            "status": (
                "ready"
                if all(madde["status"] == "ready" for madde in maddeler)
                else "partially_configured"
            ),
            "ready_count": sum(madde["status"] == "ready" for madde in maddeler),
            "total_count": len(maddeler),
            "capabilities": maddeler,
        }

    summary = ozet


CapabilityService = YetenekServisi
