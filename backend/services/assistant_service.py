import os


def yedek_cevap_olustur(soru: str, hesap_ozeti: str) -> str:
    kucuk_soru = soru.lower()
    if any(terim in kucuk_soru for terim in ("rfq", "talep")):
        return f"RFQ Avı modülünde ürün ve ülke seçerek açık satın alma taleplerini tarayabilirsiniz. {hesap_ozeti}"
    if any(terim in kucuk_soru for terim in ("yetkili", "kişi", "satın alma müdürü")):
        return "Yetkili Kişi modülü yalnız kamusal ve kaynak bağlantısı bulunan kişileri listeler; e-posta tahmini yapmaz."
    if any(terim in kucuk_soru for terim in ("fuar", "excel", "csv")):
        return "Fuar Analizi modülüne XLSX/CSV yükleyin, firma adı sütununu seçin ve analizi başlatın."
    return f"Pusula; müşteri, RFQ, yetkili kişi ve fuar katılımcısı araştırmalarını tek panelde toplar. {hesap_ozeti}"


build_fallback_answer = yedek_cevap_olustur


def soruyu_cevapla(
    question: str,
    account_summary: str,
    history: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    yedek_cevap = yedek_cevap_olustur(question, account_summary)
    if not os.getenv("OPENAI_API_KEY"):
        return yedek_cevap, "fallback"

    try:
        from openai import OpenAI

        son_gecmis = [
            {"role": oge["role"], "content": oge["content"][:1500]}
            for oge in (history or [])[-8:]
            if oge.get("role") in {"user", "assistant"} and oge.get("content")
        ]
        yanit = OpenAI().chat.completions.create(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "Pusula dış ticaret uygulamasının Türkçe yardım asistanısın. Yalnız verilen hesap özetini kullan; veri uydurma ve kullanıcı adına işlem yapma.",
                },
                *son_gecmis,
                {
                    "role": "user",
                    "content": f"Hesap özeti: {account_summary}\nSoru: {question}",
                },
            ],
        )
        cevap = yanit.choices[0].message.content
        return cevap or yedek_cevap, "ai"
    except Exception:
        return yedek_cevap, "fallback"


answer_question = soruyu_cevapla
