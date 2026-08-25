import json
import os
import re
from openai import OpenAI

SISTEM_TALIMATI = """
Sen uzman bir teknik çevirmen ve endüstriyel terminoloji mühendisisin. 
Görevin, kullanıcı tarafından sağlanan ürün adını (terimi) almak ve aşağıdaki adımları izleyerek yapılandırılmış bir JSON çıktısı üretmektir:

1. ÖNERİ: Gelen ürün adı için endüstriyel kullanıma uygun İngilizce teknik terim öner. Harici sözlüklere erişimin yoksa doğrulanmış olduğunu iddia etme.
2. ÇEVİRİ: Bulunan bu doğru teknik terimi, makine çevirisi (Google Translate) kullanmadan, doğrudan sektördeki profesyonel karşılıklarını kullanarak 50 farklı dile çevir.
3. KURAL: Asla günlük dil kullanma. Sadece mühendislik, üretim, dış ticaret ve B2B endüstriyel standartlarda kabul gören teknik terimleri tercih et.
4. ÇIKTI FORMATI: Sadece ve sadece geçerli bir JSON objesi döndür. Öncesinde veya sonrasında hiçbir açıklama metni, markdown (```json) veya yorum ekleme.

JSON yapısı şu şekilde olmalıdır:
{
  "original_input": "Kullanıcıdan gelen kelime",
  "validated_technical_term_en": "AI tarafından önerilen İngilizce Teknik Terim",
  "translations": {
    "tr": "Türkçe teknik terim",
    "de": "Almanca teknik terim",
    "fr": "Fransızca teknik terim",
    "es": "İspanyolca teknik terim",
    "zh": "Çince teknik terim"
  }
}
"""


class YapayZekaCeviriServisi:
    def __init__(self):
        api_anahtari = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_anahtari) if api_anahtari else None

    def urun_adini_cevir(self, product_name: str) -> dict:
        if self.client is None:
            return self._kanit_ekle({
                "original_input": product_name,
                "validated_technical_term_en": product_name,
                "translations": {"tr": product_name, "en": product_name},
            }, "fallback_suggested")
        try:
            yanit = self.client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": SISTEM_TALIMATI},
                    {"role": "user", "content": product_name}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            sonuc_json = yanit.choices[0].message.content
            return self._kanit_ekle(json.loads(sonuc_json), "ai_suggested")
        except Exception:
            ingilizce = QUICK_DICT.get(product_name.lower().strip(), product_name)
            return self._kanit_ekle({
                "original_input": product_name,
                "validated_technical_term_en": ingilizce,
                "translations": {"tr": product_name, "en": ingilizce},
            }, "fallback_suggested")

    @staticmethod
    def _kanit_ekle(sonuc: dict, durum: str) -> dict:
        terim = sonuc.get("validated_technical_term_en") or sonuc.get("original_input") or ""
        url_metni = re.sub(r"[^a-z0-9]+", "-", terim.lower()).strip("-")
        sonuc["verification_status"] = durum
        sonuc["evidence"] = [
            {
                "source": "IATE",
                "status": "manual_check_required",
                "url": "https://iate.europa.eu/home",
            },
            {
                "source": "Cambridge Dictionary",
                "status": "manual_check_required",
                "url": f"https://dictionary.cambridge.org/dictionary/english/{url_metni}",
            },
        ]
        return sonuc

    translate_product_name = urun_adini_cevir
    _with_evidence = _kanit_ekle


AITranslationService = YapayZekaCeviriServisi
