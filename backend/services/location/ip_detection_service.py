import logging
import re
import urllib.request
import json

from services.location.interfaces import IIpProvider
from schemas.location_schema import IPResult

logger = logging.getLogger(__name__)

_KURUMSAL_KALIPLAR = re.compile(
    r"\b(ltd|a\.?ş\.?|a\.?s\.?|inc\.?|corp\.?|llc\.?|gmbh|s\.?a\.?|pvt|"
    r"holding|group|teknoloji|technology|solutions|systems|"
    r"ticaret|sanayi|industri|global|international|enterprise|"
    r"universit\w*|üniversit\w*|hastane|hospital|bank|banka)\b",
    re.IGNORECASE,
)
_CORPORATE_PATTERNS = _KURUMSAL_KALIPLAR

_TUKETICI_ISP_KALIPLARI = re.compile(
    r"\b(turkcell|vodafone|türk telekom|superonline|ttnet|bsnl|"
    r"comcast|at&t|verizon|cox|spectrum|charter|orange|sfr|bouygues)\b",
    re.IGNORECASE,
)
_CONSUMER_ISP_PATTERNS = _TUKETICI_ISP_KALIPLARI


def _kurumsal_ag_mi(org: str | None, isp: str | None) -> bool:
    birlesik = f"{org or ''} {isp or ''}".strip()
    if not birlesik:
        return False
    if _TUKETICI_ISP_KALIPLARI.search(birlesik):
        return False
    return bool(_KURUMSAL_KALIPLAR.search(birlesik))


_is_corporate_network = _kurumsal_ag_mi


class IpApiServisi(IIpProvider):
    SAGLAYICI_ADI = "ip-api.com"
    PROVIDER_NAME = SAGLAYICI_ADI
    _BASE_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,org,isp,query"

    def __init__(self, localhost_test_ip: str = "85.105.150.10"):
        self.localhost_test_ip = localhost_test_ip

    def coz(self, ip_address: str) -> IPResult | None:
        ip = self._ip_cozumle(ip_address)
        url = self._BASE_URL.format(ip=ip)

        try:
            istek = urllib.request.Request(
                url,
                headers={"User-Agent": "PusulaApp/2.0 (ip-lookup)"},
            )
            with urllib.request.urlopen(istek, timeout=8) as cevap:
                veri = json.loads(cevap.read())

            if veri.get("status") != "success":
                logger.warning("ip-api.com başarısız: %s", veri.get("message"))
                return None

            kurum = veri.get("org")
            saglayici = veri.get("isp")

            return IPResult(
                ip=veri.get("query", ip),
                org=kurum,
                isp=saglayici,
                is_corporate=_kurumsal_ag_mi(kurum, saglayici),
                country=veri.get("country"),
                city=veri.get("city"),
                region=veri.get("regionName"),
                latitude=veri.get("lat"),
                longitude=veri.get("lon"),
            )

        except Exception as exc:
            logger.error("IpApiServisi hatası: %s", exc)
            return None

    lookup = coz

    def _ip_cozumle(self, ip: str) -> str:
        if not ip or ip in ("127.0.0.1", "::1", "browser", "localhost"):
            logger.debug("Localhost IP tespit edildi → test IP kullanılıyor: %s", self.localhost_test_ip)
            return self.localhost_test_ip
        return ip

    _resolve_ip = _ip_cozumle


IpApiService = IpApiServisi


class IpapiCoServisi(IIpProvider):
    SAGLAYICI_ADI = "ipapi.co"
    PROVIDER_NAME = SAGLAYICI_ADI
    _BASE_URL = "https://ipapi.co/{ip}/json/"

    def __init__(self, localhost_test_ip: str = "85.105.150.10"):
        self.localhost_test_ip = localhost_test_ip

    def coz(self, ip_address: str) -> IPResult | None:
        ip = ip_address
        if not ip or ip in ("127.0.0.1", "::1", "browser", "localhost"):
            ip = self.localhost_test_ip

        url = self._BASE_URL.format(ip=ip)

        try:
            istek = urllib.request.Request(
                url,
                headers={"User-Agent": "PusulaApp/2.0 (ip-lookup-fallback)"},
            )
            with urllib.request.urlopen(istek, timeout=8) as cevap:
                veri = json.loads(cevap.read())

            if veri.get("error"):
                logger.warning("ipapi.co hatası: %s", veri.get("reason"))
                return None

            kurum = veri.get("org")
            return IPResult(
                ip=ip,
                org=kurum,
                isp=None,
                is_corporate=_kurumsal_ag_mi(kurum, None),
                country=veri.get("country_name"),
                city=veri.get("city"),
                region=veri.get("region"),
                latitude=veri.get("latitude"),
                longitude=veri.get("longitude"),
            )

        except Exception as exc:
            logger.error("IpapiCoServisi hatası: %s", exc)
            return None

    lookup = coz


IpapiCoService = IpapiCoServisi
