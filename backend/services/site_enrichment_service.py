import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from services.public_page_service import PublicPageService
from services.public_url_service import safe_public_url


class SiteZenginlestirmeServisi:
    def __init__(self, page_service: PublicPageService | None = None):
        self.page_service = page_service or PublicPageService()

    def kazi(self, value: str) -> dict:
        sonuc = {
            "source_url": value, "company_name": None, "phone": None, "email": None,
            "address": None, "country": None, "about_us_text": None, "contact_text": None,
            "access_status": "enrichment_blocked",
        }
        sayfa = self.page_service.fetch(value, timeout=7)
        sonuc["source_url"] = sayfa.source_url
        sonuc["access_status"] = sayfa.access_status
        if sayfa.access_status != "public":
            return sonuc

        metin, corba = self._metni_cikar(sayfa.html)
        sonuc["about_us_text"] = metin[:4000]

        iletisim_urli = self._iletisim_urli_bul(corba, sayfa.source_url)
        if iletisim_urli:
            iletisim_sayfasi = self.page_service.fetch(iletisim_urli, timeout=7)
            if iletisim_sayfasi.access_status == "public":
                iletisim_metni, _ = self._metni_cikar(iletisim_sayfasi.html)
                sonuc["contact_text"] = iletisim_metni[:4000]
                metin = f"{metin} {iletisim_metni}"

        sonuc["email"] = self._ilk_epostayi_bul(metin)
        sonuc["phone"] = self._ilk_telefonu_bul(metin)
        return sonuc

    scrape = kazi

    @staticmethod
    def _metni_cikar(html: str) -> tuple[str, BeautifulSoup]:
        corba = BeautifulSoup(html[:2_000_000], "html.parser")
        for etiket in corba(["script", "style", "noscript", "svg"]):
            etiket.decompose()
        return " ".join(corba.get_text(" ", strip=True).split())[:12000], corba

    _text = _metni_cikar

    @staticmethod
    def _iletisim_urli_bul(soup: BeautifulSoup, base_url: str) -> str | None:
        for baglanti in soup.select("a[href]"):
            adres = str(baglanti.get("href") or "")
            etiket = f"{baglanti.get_text(' ', strip=True)} {adres}".lower()
            if any(kelime in etiket for kelime in ("contact", "iletisim", "iletişim", "kontakt")):
                return safe_public_url(urljoin(base_url, adres))
        return None

    _contact_url = _iletisim_urli_bul

    @staticmethod
    def _ilk_epostayi_bul(text: str) -> str | None:
        bulunanlar = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        gecerliler = [eposta for eposta in bulunanlar if not any(eposta.lower().endswith(uzanti) for uzanti in (".png", ".jpg", ".gif"))]
        return gecerliler[0] if gecerliler else None

    _first_email = _ilk_epostayi_bul

    @staticmethod
    def _ilk_telefonu_bul(text: str) -> str | None:
        bulunanlar = re.findall(r"\+?\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}", text)
        return bulunanlar[0] if bulunanlar else None

    _first_phone = _ilk_telefonu_bul


SiteEnrichmentService = SiteZenginlestirmeServisi
