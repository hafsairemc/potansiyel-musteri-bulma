class IstihbaratDisaAktarimServisi:
    @staticmethod
    def rfq_talepleri(rows) -> list[dict]:
        return [{
            "Talep": satir.title,
            "Alıcı / Kurum": satir.buyer_name,
            "Ülke": satir.country,
            "Miktar": satir.quantity,
            "Son Tarih": satir.deadline,
            "Açıklama": satir.description,
            "Platform": satir.platform,
            "Erişim": satir.access_status,
            "İlgililik Skoru": satir.relevance_score,
            "Güncellik Skoru": satir.freshness_score,
            "Güven Skoru": satir.confidence_score,
            "Gerekçe": satir.match_reason,
            "Kaynak": satir.source_url,
        } for satir in rows]

    rfq = rfq_talepleri

    @staticmethod
    def fuar_analizleri(rows) -> list[dict]:
        sonuc = []
        for satir in rows:
            oge = dict(satir.original_data or {})
            oge.update({
                "Analiz | Satır": satir.row_number,
                "Analiz | Firma": satir.company_name,
                "Analiz | Website": satir.website,
                "Analiz | Ülke": satir.country,
                "Analiz | Şehir": satir.city,
                "Analiz | Sektör": satir.sector,
                "Analiz | Açıklama": satir.description,
                "Analiz | E-posta": satir.email,
                "Analiz | Telefon": satir.phone,
                "Analiz | Erişim": satir.access_status,
                "Analiz | Sınıf": satir.classification,
                "Analiz | İlgililik Skoru": satir.relevance_score,
                "Analiz | Alıcı Skoru": satir.buyer_score,
                "Analiz | Eşleşen Terimler": ", ".join(satir.matched_terms or []),
                "Analiz | Gerekçe": satir.match_reason,
            })
            sonuc.append(oge)
        return sonuc

    fair = fuar_analizleri


IntelligenceExportService = IstihbaratDisaAktarimServisi
