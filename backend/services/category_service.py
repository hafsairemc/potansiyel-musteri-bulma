import re
from copy import deepcopy
from difflib import SequenceMatcher
from typing import Any

KATALOG: list[dict[str, Any]] = [
    {"id": "automotive", "name": "Otomotiv - Taşıt Araçları", "keywords": ["otomotiv", "oto", "araç", "yedek parça", "egzoz", "motor", "fren", "filtre", "rulman", "lastik"], "subcategories": [
        {"id": "exhaust", "name": "Egzoz Sistemi Parçaları", "keywords": ["egzoz", "egsoz", "egzost", "susturucu", "muffler", "exhaust"], "aliases": {"egzoz takozu": ["egzoz askı lastiği", "egzoz bağlantı lastiği", "egzoz kauçuk takozu", "exhaust rubber mount", "exhaust hanger", "muffler hanger", "exhaust isolator"]}},
        {"id": "spare-parts", "name": "Otomotiv Yedek Parça", "keywords": ["yedek parça", "fren", "filtre", "debriyaj", "radyatör", "amortisör", "rot", "aks"]},
        {"id": "tires", "name": "Lastik ve Kauçuk Parçalar", "keywords": ["lastik", "kauçuk", "conta", "takoz", "rubber"]},
    ]},
    {"id": "food", "name": "Gıda Sanayii", "keywords": ["gıda", "meyve", "sebze", "yağ", "zeytin", "elma", "un", "bakliyat", "içecek", "baharat"], "subcategories": [
        {"id": "fresh-produce", "name": "Taze Meyve ve Sebze", "keywords": ["elma", "armut", "üzüm", "kiraz", "meyve", "sebze", "fresh fruit"], "aliases": {"elma": ["taze elma", "sofralık elma", "fresh apple", "apple fruit"]}, "negative": ["iphone", "macbook", "ipad", "apple store", "ios", "technology"]},
        {"id": "oils", "name": "Yağlar ve Zeytin Ürünleri", "keywords": ["zeytinyağı", "ayçiçek yağı", "bitkisel yağ", "zeytin"]},
    ]},
    {"id": "machinery", "name": "Makine Sanayii", "keywords": ["makine", "ekipman", "tezgah", "pompa", "kompresör", "konveyör", "machine"]},
    {"id": "agriculture", "name": "Tarım Endüstrisi", "keywords": ["tarım", "tohum", "gübre", "sera", "sulama", "agriculture"]},
    {"id": "agri-machinery", "name": "Tarım Makineleri", "keywords": ["traktör", "biçerdöver", "tarım makinesi", "pulluk"]},
    {"id": "textile", "name": "Tekstil Ürünleri", "keywords": ["tekstil", "kumaş", "iplik", "dokuma", "örgü", "fabric", "textile"]},
    {"id": "apparel", "name": "Hazır Giyim - Moda", "keywords": ["giyim", "elbise", "tişört", "pantolon", "ceket", "moda"]},
    {"id": "chemicals", "name": "Kimya Sanayii", "keywords": ["kimya", "kimyasal", "boya", "reçine", "solvent", "chemical"]},
    {"id": "construction", "name": "Yapı ve İnşaat", "keywords": ["inşaat", "yapı", "çimento", "tuğla", "yalıtım", "kapı", "construction"]},
    {"id": "marble-mining", "name": "Mermer Madencilik", "keywords": ["mermer", "granit", "traverten", "maden", "marble"]},
    {"id": "metal", "name": "Metal Demir Çelik", "keywords": ["metal", "demir", "çelik", "alüminyum", "profil", "sac"]},
    {"id": "plastics", "name": "Plastik Lastik Sanayii", "keywords": ["plastik", "polimer", "kauçuk", "lastik", "plastic"]},
    {"id": "medical", "name": "Medikal ve Sağlık Ürünleri", "keywords": ["medikal", "tıbbi", "sağlık", "eldiven", "maske", "medical"]},
    {"id": "electronics", "name": "Elektrik ve Elektronik", "keywords": ["elektrik", "elektronik", "kablo", "sensör", "pano", "electronic"]},
    {"id": "furniture", "name": "Mobilya", "keywords": ["mobilya", "koltuk", "masa", "sandalye", "dolap", "furniture"]},
    {"id": "packaging", "name": "Ambalaj Kağıt Matbaa", "keywords": ["ambalaj", "paket", "kutu", "etiket", "kağıt", "packaging"]},
    {"id": "cosmetics", "name": "Kozmetik Ürünler", "keywords": ["kozmetik", "şampuan", "krem", "parfüm", "cosmetic"]},
    {"id": "hygiene", "name": "Hijyen - Temizlik Ürünleri", "keywords": ["temizlik", "deterjan", "dezenfektan", "hijyen"]},
    {"id": "energy", "name": "Enerji Sektörü", "keywords": ["enerji", "güneş paneli", "solar", "jeneratör", "batarya"]},
    {"id": "hvac", "name": "Isıtma Soğutma Havalandırma", "keywords": ["ısıtma", "soğutma", "havalandırma", "klima", "hvac"]},
    {"id": "industrial", "name": "Endüstriyel Ürünler", "keywords": ["endüstriyel", "sanayi", "hırdavat", "bağlantı elemanı", "industrial"]},
    {"id": "defense", "name": "Savunma Sanayii", "keywords": ["savunma", "askeri", "zırh", "defense"]},
    {"id": "marine", "name": "Deniz Araç ve Gereçleri", "keywords": ["deniz", "gemi", "tekne", "marine"]},
    {"id": "services", "name": "Hizmet Sektörü", "keywords": ["hizmet", "danışmanlık", "lojistik", "service"]},
    {"id": "import-export", "name": "İhracat - İthalat", "keywords": ["ihracat", "ithalat", "dış ticaret", "export", "import"]},
]

CATALOG = KATALOG


def _metni_normallestir(deger: str) -> str:
    return re.sub(r"[^a-z0-9çğıöşü ]+", " ", (deger or "").lower()).strip()


_norm = _metni_normallestir


class KategoriServisi:
    def kategorileri_listele(self) -> list[dict]:
        return deepcopy(KATALOG)

    list_categories = kategorileri_listele

    def siniflandir(self, product_name: str) -> dict:
        metin = _metni_normallestir(product_name)
        sirali: list[tuple[int, dict[str, Any], dict[str, Any] | None]] = []

        for kategori in KATALOG:
            kategori_eslesmeleri = [
                anahtar for anahtar in kategori["keywords"]
                if _metni_normallestir(anahtar) in metin or metin in _metni_normallestir(anahtar)
            ]
            en_iyi_alt: dict[str, Any] | None = None
            en_iyi_alt_skor = 0.0

            for alt in kategori.get("subcategories", []):
                alt_eslesmeleri = [
                    anahtar for anahtar in alt["keywords"]
                    if _metni_normallestir(anahtar) in metin or metin in _metni_normallestir(anahtar)
                ]
                skor = (
                    70 if alt_eslesmeleri
                    else max((SequenceMatcher(None, metin, _metni_normallestir(anahtar)).ratio() * 45 for anahtar in alt["keywords"]), default=0)
                )
                if skor > en_iyi_alt_skor:
                    en_iyi_alt, en_iyi_alt_skor = alt, skor

            kategori_skor = (
                65 if kategori_eslesmeleri
                else max((SequenceMatcher(None, metin, _metni_normallestir(anahtar)).ratio() * 40 for anahtar in kategori["keywords"]), default=0)
            )
            toplam_skor = min(100, int(max(kategori_skor, en_iyi_alt_skor) + (15 if kategori_eslesmeleri and en_iyi_alt_skor >= 65 else 0)))
            sirali.append((toplam_skor, kategori, en_iyi_alt))

        sirali.sort(key=lambda satir: satir[0], reverse=True)
        oneriler = [self._profil_olustur(product_name, skor, kat, alt) for skor, kat, alt in sirali[:3]]
        return {"product_name": product_name, "confidence": oneriler[0]["confidence"], "suggestions": oneriler}

    classify = siniflandir

    def _profil_olustur(self, product_name: str, score: int, category: dict, sub: dict | None) -> dict:
        es_anlamlilar = []
        negatifler = []
        if sub:
            es_anlamli_haritasi = sub.get("aliases", {})
            es_anlamlilar = es_anlamli_haritasi.get(_metni_normallestir(product_name), [])
            negatifler = sub.get("negative", [])

        ingilizce_isaretcileri = ("exhaust", "hanger", "muffler", "isolator", "fresh", "apple", "fruit", "mount")
        ingilizce_es_anlamlilar = [a for a in es_anlamlilar if any(kelime in a.lower() for kelime in ingilizce_isaretcileri)]
        turkce_es_anlamlilar = [a for a in es_anlamlilar if a not in ingilizce_es_anlamlilar]

        return {
            "category_id": category["id"],
            "category_name": category["name"],
            "subcategory_id": sub["id"] if sub else None,
            "subcategory_name": sub["name"] if sub else None,
            "product_group": sub["name"] if sub else category["name"],
            "category": category["name"],
            "subcategory": sub["name"] if sub else None,
            "aliases_tr": turkce_es_anlamlilar,
            "aliases_en": ingilizce_es_anlamlilar,
            "negative_keywords": negatifler,
            "negative_terms": negatifler,
            "category_keywords": list(dict.fromkeys(category["keywords"] + (sub.get("keywords", []) if sub else []))),
            "target_customer_types": ["ithalatçı", "distribütör", "toptancı", "bayi"],
            "confidence": max(15, score),
        }

    _profile = _profil_olustur


CategoryService = KategoriServisi
