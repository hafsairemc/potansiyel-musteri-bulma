DERSLER = (
    {
        "key": "urun-profili", "title": "Doğru ürün profili hazırlama", "duration_minutes": 8,
        "summary": "Ürün adı, GTİP, OEM, sektör ve olumsuz terimleri doğru tanımlayın.",
        "sections": (
            "Ürünün teknik ve ticari adını ayrı düşünün. Alıcının aradığı terim çoğu zaman üretimde kullanılan teknik addır.",
            "GTİP ürün grubunu, OEM ise parça uyumluluğunu güçlendirir. Bilmediğiniz kodu tahmin ederek girmeyin.",
            "Alakasız anlamları olumsuz terimlere ekleyerek arama sonucundaki gürültüyü azaltın.",
        ),
        "question": "Bilmediğiniz bir GTİP kodu için doğru davranış hangisidir?",
        "options": ("Yakın bir kod tahmin etmek", "Boş bırakıp doğruladıktan sonra eklemek", "Ürün adını GTİP alanına yazmak"),
        "correct_answer": 1,
    },
    {
        "key": "hedef-pazar", "title": "Hedef pazar seçimi", "duration_minutes": 10,
        "summary": "Ülke, dil ve alıcı türüne göre arama kapsamı oluşturun.",
        "sections": (
            "Pazar büyüklüğünü yalnız firma sayısıyla değil, ithalat değeri ve ürün uyumuyla birlikte değerlendirin.",
            "Yerel dildeki ürün adı ile importer, distributor ve wholesaler gibi alıcı sinyallerini birlikte kullanın.",
            "İlk denemede birkaç ülke seçip sonuç kalitesini ölçmek, bütün dünyayı aynı anda taramaktan daha kontrollüdür.",
        ),
        "question": "Hedef pazarı değerlendirirken hangi veri birlikte kullanılmalıdır?",
        "options": ("Yalnız nüfus", "Yalnız firma sayısı", "İthalat değeri, ürün uyumu ve alıcı sinyali"),
        "correct_answer": 2,
    },
    {
        "key": "musteri-dogrulama", "title": "Potansiyel müşteriyi doğrulama", "duration_minutes": 12,
        "summary": "Kaynak, firma sitesi, iletişim ve alıcı sinyallerini birlikte değerlendirin.",
        "sections": (
            "Bir arama sonucu tek başına müşteri kanıtı değildir. Firma sitesi ve kaynak sayfasını açarak faaliyet alanını kontrol edin.",
            "Satın alma, ithalat ve dağıtım ifadeleri alıcı sinyalidir; yalnız üretici olması her zaman müşteri olduğu anlamına gelmez.",
            "İletişim bilgisinin hangi kamusal kaynaktan geldiğini koruyun ve güven skorunu karar desteği olarak kullanın.",
        ),
        "question": "Bir firmanın potansiyel müşteri olduğuna karar vermek için ne yeterlidir?",
        "options": ("Yalnız şirket adı", "Kaynak, faaliyet ve alıcı sinyallerinin birlikte doğrulanması", "Yalnız e-posta bulunması"),
        "correct_answer": 1,
    },
    {
        "key": "rfq-fuar", "title": "RFQ ve fuar listeleriyle çalışma", "duration_minutes": 9,
        "summary": "Açık talepleri ve katılımcı listelerini puanlayıp kısa liste oluşturun.",
        "sections": (
            "RFQ sonucunda ürün, tarih, miktar ve kaynak bağlantısını birlikte kontrol edin.",
            "Fuar listesindeki sütunları doğru eşleyin; firma adı zorunlu, web sitesi ve açıklama kaliteyi artıran alanlardır.",
            "CAPTCHA veya giriş isteyen platformları aşmaya çalışmayın; kaynak bağlantısını açıp işlemi platformda tamamlayın.",
        ),
        "question": "Giriş korumalı bir RFQ sayfasında ne yapılmalıdır?",
        "options": ("Koruma aşılmalıdır", "Sonuç silinmelidir", "Giriş gerekli etiketiyle platforma yönlendirilmelidir"),
        "correct_answer": 2,
    },
    {
        "key": "guvenli-iletisim", "title": "Güvenli ilk iletişim", "duration_minutes": 7,
        "summary": "Kaynak kanıtını koruyun, kişiselleştirin ve gönderim öncesi onay verin.",
        "sections": (
            "Mesajı alıcının şirketi ve rolüyle ilişkilendirin; toplu ve ilgisiz metinlerden kaçının.",
            "Tahmin edilmiş adres yerine kamusal kaynağı bulunan veya kullanıcı tarafından eklenen e-postayı kullanın.",
            "Gönderimden önce alıcı listesini onaylayın ve abonelikten çıkma taleplerine yeniden e-posta göndermeyin.",
        ),
        "question": "Bir kampanya ne zaman gönderim kuyruğuna alınmalıdır?",
        "options": ("Taslak oluşturulur oluşturulmaz", "Kullanıcı alıcıları kontrol edip açık onay verdikten sonra", "Her yeni firma bulunduğunda"),
        "correct_answer": 1,
    },
)

LESSONS = DERSLER


def anahtara_gore_ders(key: str):
    return next((ders for ders in DERSLER if ders["key"] == key), None)


lesson_by_key = anahtara_gore_ders


def kamusal_ders(lesson: dict) -> dict:
    return {anahtar: deger for anahtar, deger in lesson.items() if anahtar != "correct_answer"}


public_lesson = kamusal_ders


def cevap_dogru_mu(key: str, answer_index: int) -> bool:
    ders = anahtara_gore_ders(key)
    return bool(ders and ders["correct_answer"] == answer_index)


answer_is_correct = cevap_dogru_mu
