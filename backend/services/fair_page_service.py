import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from services.public_page_service import PublicPageService


@dataclass(frozen=True)
class FuarSayfaSonucu:
    source_url: str
    access_status: str
    entries: tuple[tuple[str, str], ...] = ()


FairPageResult = FuarSayfaSonucu


class FuarSayfaServisi:
    profil_terimleri = (
        "exhibitor",
        "participant",
        "company",
        "vendor",
        "sponsor",
        "katilimci",
        "katılımcı",
        "firma",
        "aussteller",
        "exposant",
    )
    profile_terms = profil_terimleri

    yoksayilan_etiketler = {
        "home",
        "anasayfa",
        "contact",
        "iletişim",
        "login",
        "giriş",
        "register",
        "menu",
        "next",
        "previous",
        "read more",
        "detay",
    }
    ignored_labels = yoksayilan_etiketler

    def __init__(self, page_service: PublicPageService | None = None):
        self.page_service = page_service or PublicPageService()

    def ayikla(self, source_url: str) -> FuarSayfaSonucu:
        sayfa = self.page_service.fetch(source_url)
        if sayfa.access_status != "public":
            return FuarSayfaSonucu(sayfa.source_url, sayfa.access_status)

        corba = BeautifulSoup(sayfa.html, "html.parser")
        for etiket in corba(["script", "style", "noscript", "svg"]):
            etiket.decompose()

        kayitlar = self._baglantili_kayitlar(corba, sayfa.source_url)
        if not kayitlar:
            kayitlar = self._metin_kayitlari(corba)

        return FuarSayfaSonucu(sayfa.source_url, "public", tuple(kayitlar[:1000]))

    extract = ayikla

    def _baglantili_kayitlar(self, soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
        kayitlar = []
        gorulenler = set()
        for baglanti in soup.select("a[href]"):
            href = str(baglanti.get("href") or "").strip()
            etiket = self._etiketi_temizle(baglanti.get_text(" ", strip=True))
            icerik = " ".join(
                str(deger or "")
                for deger in (
                    href,
                    baglanti.get("class"),
                    baglanti.parent.get("class") if baglanti.parent else "",
                    baglanti.parent.get("id") if baglanti.parent else "",
                )
            ).casefold()

            if not any(terim in icerik for terim in self.profil_terimleri):
                continue
            website = self._web_adresi(urljoin(base_url, href))
            if not website or not self._gecerli_etiket_mi(etiket):
                continue

            anahtar = (etiket.casefold(), website.casefold())
            if anahtar not in gorulenler:
                gorulenler.add(anahtar)
                kayitlar.append((etiket, website))
        return kayitlar

    _linked_entries = _baglantili_kayitlar

    def _metin_kayitlari(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        secici = ",".join(
            f'[class*="{terim}" i], [id*="{terim}" i]' for terim in self.profil_terimleri
        )
        kayitlar = []
        gorulenler = set()
        for oge in soup.select(secici):
            etiket = self._etiketi_temizle(oge.get_text(" ", strip=True))
            anahtar = etiket.casefold()
            if self._gecerli_etiket_mi(etiket) and anahtar not in gorulenler:
                gorulenler.add(anahtar)
                kayitlar.append((etiket, ""))
        return kayitlar

    _text_entries = _metin_kayitlari

    def _gecerli_etiket_mi(self, value: str) -> bool:
        kucuk = value.casefold()
        return 2 <= len(value) <= 160 and kucuk not in self.yoksayilan_etiketler and len(value.split()) <= 16

    _valid_label = _gecerli_etiket_mi

    @staticmethod
    def _etiketi_temizle(value: str) -> str:
        return " ".join(re.sub(r"[\r\n\t]+", " ", value).split()).strip(" -|•")

    _clean_label = _etiketi_temizle

    @staticmethod
    def _web_adresi(value: str) -> str:
        ayristirilmis = urlparse(value)
        if ayristirilmis.scheme not in {"http", "https"} or not ayristirilmis.hostname or ayristirilmis.username or ayristirilmis.password:
            return ""
        return value

    _web_url = _web_adresi


FairPageService = FuarSayfaServisi
