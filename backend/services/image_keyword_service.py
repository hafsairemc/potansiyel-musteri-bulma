import base64
import json
import os


class GorselAnahtarKelimeServisi:
    def ayikla(self, content: bytes, media_type: str) -> list[str]:
        if not os.getenv("OPENAI_API_KEY"):
            return []
        try:
            from openai import OpenAI

            kodlanmis = base64.b64encode(content).decode("ascii")
            yanit = OpenAI().chat.completions.create(
                model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": 'Görseldeki ticari ürünü tanımla. Sadece JSON döndür: {"keywords":[Türkçe ve İngilizce teknik arama terimleri]}. Marka veya kesin model uydurma.',
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Bu ürün için en fazla 8 kısa B2B arama terimi üret."},
                            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{kodlanmis}"}},
                        ],
                    },
                ],
            )
            veri = json.loads(yanit.choices[0].message.content or "{}")
            anahtar_kelimeler = [str(deger).strip() for deger in veri.get("keywords", []) if str(deger).strip()]
            return list(dict.fromkeys(anahtar_kelimeler))[:8]
        except Exception:
            return []

    extract = ayikla


ImageKeywordService = GorselAnahtarKelimeServisi
