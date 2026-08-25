import re
import unicodedata
from typing import Any

ALICI_SINYALLERI = {
    "importer": 22, "import": 12, "buyer": 22, "purchasing": 15,
    "wholesaler": 20, "wholesale": 14, "distributor": 20,
    "dealer": 12, "stockist": 12, "reseller": 10,
    "ithalatci": 22, "ithalat": 12, "alici": 22, "toptanci": 20,
    "toptan": 14, "bayi": 12,
}
BUYER_SIGNALS = ALICI_SINYALLERI

SATICI_SINYALLERI = (
    "manufacturer", "producer", "supplier", "exporter", "factory",
    "manufacturing", "uretici", "tedarikci", "ihracatci", "fabrika",
)
SELLER_SIGNALS = SATICI_SINYALLERI


def _metni_normallestir(deger: str) -> str:
    deger = unicodedata.normalize("NFKD", deger or "")
    deger = "".join(karakter for karakter in deger if not unicodedata.combining(karakter))
    return re.sub(r"[^a-z0-9]+", " ", deger.lower()).strip()


_normalize = _metni_normallestir


class FirmaAnalizServisi:
    def firmayi_analiz_et(
        self,
        company_name: str,
        product_name: str,
        about_us_text: str,
        contact_text: str,
        search_profile: dict[str, Any] | None = None,
        source: str = "google_web",
    ) -> dict[str, Any]:
        profil = search_profile or {}
        baslik = _metni_normallestir(company_name)
        birlesik = _metni_normallestir(f"{company_name or ''} {about_us_text or ''} {contact_text or ''}")
        es_anlamlilar = [product_name, *(profil.get("aliases_tr") or []), *(profil.get("aliases_en") or [])]
        terimler = list(dict.fromkeys(_metni_normallestir(terim) for terim in es_anlamlilar if _metni_normallestir(terim)))
        negatifler = [_metni_normallestir(terim) for terim in profil.get("negative_terms") or []]
        kategori_terimleri = [profil.get("category"), profil.get("subcategory"), profil.get("product_group")]
        kategori_terimleri += list(profil.get("category_keywords") or [])
        kategori_terimleri = [_metni_normallestir(terim) for terim in kategori_terimleri if _metni_normallestir(terim)]

        baslik_eslesmeleri = [terim for terim in terimler if terim in baslik]
        govde_eslesmeleri = [terim for terim in terimler if terim in birlesik]
        kategori_eslesmeleri = [terim for terim in kategori_terimleri if terim in birlesik]
        negatif_eslesmeler = [terim for terim in negatifler if terim in birlesik]

        ilgi_puani = (25 if baslik_eslesmeleri else 0) + (50 if govde_eslesmeleri else 0) + (15 if kategori_eslesmeleri else 0)
        ilgi_puani = max(0, min(100, ilgi_puani - min(60, len(negatif_eslesmeler) * 30)))
        dogrudan_eslesme = bool(baslik_eslesmeleri or govde_eslesmeleri)
        harita_adayi_mi = source == "google_maps" and bool(kategori_eslesmeleri)
        ilgili_mi = (dogrudan_eslesme and ilgi_puani >= 45) or harita_adayi_mi

        alici_eslesmeleri = [sinyal for sinyal in ALICI_SINYALLERI if sinyal in birlesik]
        alici_skoru = min(100, sum(ALICI_SINYALLERI[oge] for oge in alici_eslesmeleri))
        eposta = self._eposta_cikar(f"{about_us_text or ''} {contact_text or ''}")
        telefon = self._telefon_cikar(f"{about_us_text or ''} {contact_text or ''}")
        alici_skoru = min(100, alici_skoru + (8 if eposta else 0) + (5 if telefon else 0))
        satici_eslesmeleri = [sinyal for sinyal in SATICI_SINYALLERI if sinyal in birlesik]
        musteri_tipi = "potential_customer" if alici_skoru >= 35 else ("seller_manufacturer" if satici_eslesmeleri else "sector_candidate")

        gerekceler = []
        if govde_eslesmeleri:
            gerekceler.append("Ürün eşleşti: " + ", ".join(govde_eslesmeleri[:4]))
        if kategori_eslesmeleri:
            gerekceler.append("Kategori uyumu: " + ", ".join(kategori_eslesmeleri[:3]))
        if alici_eslesmeleri:
            gerekceler.append("İthalatçı/alıcı sinyali: " + ", ".join(alici_eslesmeleri[:4]))
        if satici_eslesmeleri:
            gerekceler.append("Satıcı/üretici sinyali: " + ", ".join(satici_eslesmeleri[:3]))
        if negatif_eslesmeler:
            gerekceler.append("Olumsuz eşleşme: " + ", ".join(negatif_eslesmeler[:3]))

        return {
            "company_name": company_name or "",
            "email": eposta,
            "phone": telefon,
            "country": self._ulke_tahmin_et(birlesik),
            "is_importer": any(x in alici_eslesmeleri for x in ("importer", "import", "ithalatci", "ithalat")),
            "is_exporter": bool(satici_eslesmeleri),
            "is_distributor": "distributor" in alici_eslesmeleri,
            "is_wholesaler": any(x in alici_eslesmeleri for x in ("wholesaler", "wholesale", "toptanci", "toptan")),
            "sells_product": dogrudan_eslesme,
            "is_relevant": ilgili_mi,
            "is_potential_customer": alici_skoru >= 35,
            "is_competitor": bool(satici_eslesmeleri) and alici_skoru < 35,
            "customer_type": musteri_tipi,
            "potential_customer_score": min(100, round(ilgi_puani + alici_skoru * 0.6)),
            "relevance_score": ilgi_puani,
            "buyer_score": alici_skoru,
            "confidence_score": min(95, ilgi_puani + (10 if eposta else 0) + (5 if telefon else 0)),
            "matched_terms": list(dict.fromkeys(govde_eslesmeleri + kategori_eslesmeleri)),
            "category_path": " > ".join(filter(None, [profil.get("category"), profil.get("subcategory"), profil.get("product_group")])),
            "match_reason": ". ".join(gerekceler) or "Yeterli ürün eşleşmesi bulunamadı",
        }

    analyze_company = firmayi_analiz_et

    @staticmethod
    def _eposta_cikar(text: str) -> str | None:
        yasakli_uzantilar = (".png", ".jpg", ".gif", "example.com", "sentry.io", "wixpress.com")
        for eposta in re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text or ""):
            if not any(eposta.lower().endswith(uzanti) for uzanti in yasakli_uzantilar) and len(eposta) < 80:
                return eposta.lower()
        return None

    _extract_email = _eposta_cikar

    @staticmethod
    def _telefon_cikar(text: str) -> str | None:
        eslesme = re.search(r"(\+?\d[\d\s\-().]{6,18}\d)", text or "")
        return eslesme.group(0).strip() if eslesme else None

    _extract_phone = _telefon_cikar

    @staticmethod
    def _ulke_tahmin_et(text: str) -> str | None:
        ulkeler = {
            "turkiye": "Türkiye", "turkey": "Türkiye", "germany": "Almanya",
            "almanya": "Almanya", "france": "Fransa", "italy": "İtalya",
            "china": "Çin", "cin": "Çin", "india": "Hindistan", "united states": "ABD",
        }
        return next((ulke for terim, ulke in ulkeler.items() if terim in text), None)

    _guess_country = _ulke_tahmin_et


CompanyAnalyzerService = FirmaAnalizServisi
