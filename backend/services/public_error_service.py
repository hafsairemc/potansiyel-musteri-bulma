class GenelHataServisi:
    _mesajlar = {
        "PROVIDER_NOT_CONFIGURED": "Bu arama kaynağı henüz yapılandırılmamış.",
        "PARTIAL_PROVIDER_ERRORS": "Bazı sağlayıcı sorguları tamamlanamadı; bulunan sonuçlar korundu.",
        "RFQ_PROVIDER_ERROR": "RFQ kaynağına şu anda ulaşılamadı.",
        "CONTACT_PROVIDER_ERROR": "Yetkili kişi araması şu anda tamamlanamadı.",
        "FAIR_FILE_ERROR": "Fuar dosyası analiz edilirken hata oluştu.",
        "WORKER_ERROR": "Arka plan görevi tamamlanamadı.",
        "QUEUE_UNAVAILABLE": "Görev kuyruğuna şu anda ulaşılamıyor.",
        "ROW_LIMIT_APPLIED": "Dosyanın yapılandırılmış satır sınırına kadar olan bölümü analiz edildi.",
    }
    _messages = _mesajlar

    @classmethod
    def mesaj(cls, error_code: str | None, has_error: bool = True) -> str | None:
        if not has_error:
            return None
        return cls._mesajlar.get(error_code or "", "İşlem tamamlanamadı. Lütfen daha sonra tekrar deneyin.")

    message = mesaj


PublicErrorService = GenelHataServisi
