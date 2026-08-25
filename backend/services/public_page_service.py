from dataclasses import dataclass
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
import httpx

from services.public_url_service import safe_public_url


@dataclass(frozen=True)
class KamusalSayfa:
    source_url: str
    access_status: str
    html: str = ""


PublicPage = KamusalSayfa


class KamusalSayfaServisi:
    max_content_bytes = 2_000_000
    user_agent = "PusulaResearchBot/1.0"
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    def sayfayi_getir(self, value: str, timeout: float = 8) -> KamusalSayfa:
        url = safe_public_url(value)
        if not url:
            return KamusalSayfa(value, "enrichment_blocked")
        try:
            with httpx.Client(headers=self.headers, timeout=timeout, follow_redirects=False) as istemci:
                if not self._robots_izin_veriyor_mu(istemci, url):
                    return KamusalSayfa(url, "robots_blocked")
                yanit = self._get_istegi(istemci, url)
        except httpx.HTTPError:
            return KamusalSayfa(url, "enrichment_blocked")

        if yanit is None:
            return KamusalSayfa(url, "enrichment_blocked")

        nihai_url = str(yanit.url)
        if yanit.status_code in {401, 403}:
            return KamusalSayfa(nihai_url, "login_required")
        if yanit.status_code >= 300 or "text/html" not in yanit.headers.get("content-type", ""):
            return KamusalSayfa(nihai_url, "enrichment_blocked")

        html = yanit.text[:2_000_000]
        if self._captcha_mi(html):
            return KamusalSayfa(nihai_url, "captcha_blocked")
        return KamusalSayfa(nihai_url, "public", html)

    fetch = sayfayi_getir

    def _get_istegi(self, client: httpx.Client, value: str) -> httpx.Response | None:
        guncel = safe_public_url(value)
        for _ in range(4):
            if not guncel:
                return None
            with client.stream("GET", guncel) as akis:
                if akis.status_code in {301, 302, 303, 307, 308}:
                    guncel = safe_public_url(urljoin(guncel, akis.headers.get("location", "")))
                    continue
                icerik = bytearray()
                for parca in akis.iter_bytes():
                    icerik.extend(parca)
                    if len(icerik) > self.max_content_bytes:
                        return httpx.Response(
                            413,
                            headers=akis.headers,
                            request=akis.request,
                            content=b"",
                        )
                return httpx.Response(
                    akis.status_code,
                    headers=akis.headers,
                    request=akis.request,
                    content=bytes(icerik),
                )
        return None

    _get = _get_istegi

    def _robots_izin_veriyor_mu(self, client: httpx.Client, url: str) -> bool:
        robots_url = urljoin(url, "/robots.txt")
        yanit = self._get_istegi(client, robots_url)
        if yanit is None or yanit.status_code != 200:
            return True
        ayristirici = RobotFileParser()
        ayristirici.set_url(robots_url)
        ayristirici.parse(yanit.text.splitlines())
        return ayristirici.can_fetch(self.user_agent, url)

    _robots_allows = _robots_izin_veriyor_mu

    @staticmethod
    def _captcha_mi(value: str) -> bool:
        kucuk = value.lower()
        return any(terim in kucuk for terim in ("captcha", "verify you are human", "cloudflare challenge", "robot check"))

    _is_captcha = _captcha_mi


PublicPageService = KamusalSayfaServisi
