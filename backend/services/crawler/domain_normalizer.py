from urllib.parse import urlparse
from core.interfaces import SearchResult

ENGELLE_DOMAINS = {
    "google.com", "facebook.com", "linkedin.com", "twitter.com", "x.com",
    "instagram.com", "youtube.com", "amazon.com", "alibaba.com",
    "wikipedia.org", "wikimedia.org", "reddit.com", "pinterest.com",
    "tiktok.com", "snapchat.com", "whatsapp.com", "t.me", "telegram.org",
}
BLOCKED_DOMAINS = ENGELLE_DOMAINS

ENGELLE_YOL_KALIPLARI = [
    "/blog/", "/news/", "/article", "/help/", "/support/",
    "/faq", "/forum/", "/community/", "/tag/", "/category/",
    "/how-to", "/what-is", "/about-us-page", "/privacy", "/terms",
    "/login", "/register", "/signup", "/press/", "/media/",
    "/languages", "/free-consultation", "/purchaser/", "/supplier/how",
]
BLOCKED_PATH_PATTERNS = ENGELLE_YOL_KALIPLARI

ENGELLE_ALT_DOMAINS = {
    "help", "blog", "support", "news", "m",
    "us.solutions", "solutions", "developer",
}
BLOCKED_SUBDOMAINS = ENGELLE_ALT_DOMAINS


class AlanAdiNormallestirici:
    def __init__(self):
        self.gorulen_alan_adlari: set[str] = set()

    @property
    def seen_domains(self) -> set[str]:
        return self.gorulen_alan_adlari

    @seen_domains.setter
    def seen_domains(self, value: set[str]) -> None:
        self.gorulen_alan_adlari = value

    def alan_adini_normallestir(self, url: str) -> str:
        try:
            ayristirilmis = urlparse(url)
            sunucu = ayristirilmis.netloc.lower()
            if sunucu.startswith("www."):
                sunucu = sunucu[4:]
            return sunucu
        except Exception:
            return url.lower()

    normalize_domain = alan_adini_normallestir

    def engellendi_mi(self, url: str) -> bool:
        try:
            ayristirilmis = urlparse(url.lower())
            sunucu = ayristirilmis.netloc
            yol = ayristirilmis.path

            temiz = sunucu.replace("www.", "")
            if temiz in ENGELLE_DOMAINS:
                return True

            alt_alan_adi = sunucu.split(".")[0]
            if alt_alan_adi in ENGELLE_ALT_DOMAINS:
                return True

            if any(kalip in yol for kalip in ENGELLE_YOL_KALIPLARI):
                return True

            return False
        except Exception:
            return False

    is_blocked = engellendi_mi

    def mukerrerleri_filtrele(self, results: list[SearchResult]) -> list[SearchResult]:
        benzersiz: list[SearchResult] = []

        for sonuc in results:
            if self.engellendi_mi(sonuc.url):
                continue

            alan_adi = self.alan_adini_normallestir(sonuc.url)
            if alan_adi not in self.gorulen_alan_adlari:
                self.gorulen_alan_adlari.add(alan_adi)
                benzersiz.append(sonuc)

        return benzersiz

    filter_duplicates = mukerrerleri_filtrele


DomainNormalizer = AlanAdiNormallestirici
