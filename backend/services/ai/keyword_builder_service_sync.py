import re
import logging
from typing import Any
import httpx

from core.interfaces import SearchQuery
from services.country_search_strategy import strategy_for

logger = logging.getLogger(__name__)

B2B_PLATFORMLARI = [
    {"domain": "europages.com",       "label": "Europages"},
    {"domain": "kompass.com",          "label": "Kompass"},
    {"domain": "turkishexporter.com.tr", "label": "TurkishExporter"},
    {"domain": "turkish-manufacturers.com", "label": "Turkish Manufacturers"},
    {"domain": "tradeindia.com",       "label": "TradeIndia"},
    {"domain": "tradekey.com",         "label": "TradeKey"},
    {"domain": "ecplaza.net",          "label": "ECPlaza"},
    {"domain": "eworldtrade.com",      "label": "eWorldTrade"},
    {"domain": "indiamart.com",        "label": "IndiaMART"},
    {"domain": "made-in-china.com",    "label": "Made-in-China"},
    {"domain": "dhgate.com",           "label": "DHgate"},
    {"domain": "ec21.com",             "label": "EC21"},
    {"domain": "thomasnet.com",        "label": "Thomasnet"},
]
B2B_PLATFORMS = B2B_PLATFORMLARI


class AnahtarKelimeOlusturucuServisi:
    def sorgulari_olustur(
        self, product_data: dict[str, Any], search_context: dict[str, Any]
    ) -> list[SearchQuery]:
        urun_adi = product_data.get("product_name", "").strip()
        hedef_ulke = search_context.get("target_country", "Global")
        profil = product_data.get("search_profile") or {}
        es_anlamlilar_tr = profil.get("aliases_tr") or []
        es_anlamlilar_en = profil.get("aliases_en") or []
        gorsel_terimleri = profil.get("image_terms") or []
        urun_en = product_data.get("product_name_en") or (es_anlamlilar_en[0] if es_anlamlilar_en else self._cevir(urun_adi))

        logger.info("Çeviri: '%s' → '%s'", urun_adi, urun_en)

        kaynak = search_context.get("source", "search_engine")
        sektorler = [s for s in product_data.get("sub_sectors", []) if s]
        rakipler = [r for r in product_data.get("competitors", []) if r]
        gtip = product_data.get("hs_code", "")
        ceviriler = [terim for terim in product_data.get("translations", []) if terim]

        tam_terimler = list(dict.fromkeys([urun_adi, *es_anlamlilar_tr[:3], urun_en, *es_anlamlilar_en[:3], *ceviriler[:5], *gorsel_terimleri[:5]]))
        tirnakli_terimler = " OR ".join(f'"{terim}"' for terim in tam_terimler if terim)
        kategori = " ".join(filter(None, [profil.get("subcategory"), profil.get("product_group")]))
        olumsuz = " ".join(f'-"{terim}"' for terim in (profil.get("negative_terms") or [])[:6])

        ifadeler = [
            f'({tirnakli_terimler}) (ithalatçı OR toptancı OR distribütör OR alıcı) "{hedef_ulke}" {olumsuz}',
            f'({tirnakli_terimler}) (importer OR wholesaler OR distributor OR buyer) "{hedef_ulke}" {olumsuz}',
        ]
        if kategori:
            ifadeler.append(f'({tirnakli_terimler}) "{kategori}" "{hedef_ulke}" {olumsuz}')
        if gtip:
            ifadeler.append(f'"{gtip}" importer distributor {hedef_ulke}')
        ifadeler.extend(f'"{urun_en}" "{sektor}" {hedef_ulke}' for sektor in sektorler[:4])
        ifadeler.extend(f'"{rakip}" distributor {hedef_ulke}' for rakip in rakipler[:4])

        ulke_stratejisi = strategy_for(hedef_ulke)
        if ulke_stratejisi:
            yerel_alicilar = " OR ".join(ulke_stratejisi.buyer_terms)
            ifadeler.append(f'({tirnakli_terimler}) ({yerel_alicilar}) "{hedef_ulke}" {olumsuz}')
            ifadeler.extend(f'({tirnakli_terimler}) "{terim}" {olumsuz}' for terim in ulke_stratejisi.market_terms)

        if kaynak == "b2b_platform":
            platformlar = list(B2B_PLATFORMLARI)
            if ulke_stratejisi:
                bilinenler = {oge["domain"] for oge in platformlar}
                platformlar.extend(
                    {"domain": alan_adi, "label": alan_adi}
                    for alan_adi in ulke_stratejisi.platforms
                    if alan_adi not in bilinenler
                )
            ifadeler = [
                f'site:{platform["domain"]} ({tirnakli_terimler}) '
                f'(importer OR distributor OR wholesaler OR ithalatçı OR toptancı OR manufacturer OR üretici) "{hedef_ulke}" {olumsuz}'
                for platform in platformlar
            ]

        sorgular: list[SearchQuery] = [SearchQuery(
            query_text=ifade,
            target_country=hedef_ulke,
            search_engine="Yandex" if kaynak == "yandex_web" else "Google",
            query_type="B2B" if kaynak == "b2b_platform" else "WEB",
        ) for ifade in dict.fromkeys(ifadeler)]

        return sorgular

    build_queries = sorgulari_olustur

    def _cevir(self, text: str) -> str:
        if re.match(r'^[a-zA-Z0-9 \-]+$', text):
            return text

        try:
            url = "https://api.mymemory.translated.web/get"
            yanit = httpx.get(
                url,
                params={"q": text, "langpair": "tr|en"},
                timeout=6.0,
            )
            if yanit.status_code == 200:
                veri = yanit.json()
                cevrilen = veri.get("responseData", {}).get("translatedText", "")
                if cevrilen and cevrilen.upper() != "MYMEMORY WARNING:":
                    if len(cevrilen) < 200 and not cevrilen.startswith("MYMEMORY"):
                        return cevrilen.strip()
        except Exception as exc:
            logger.warning("MyMemory çeviri hatası: %s", exc)

        return text

    _translate = _cevir


KeywordBuilderServiceSync = AnahtarKelimeOlusturucuServisi
