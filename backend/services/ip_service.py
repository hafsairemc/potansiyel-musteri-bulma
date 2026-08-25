import ipaddress
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


class IpServisi:
    @staticmethod
    def ipten_konum_getir(ip_address: str):
        try:
            adres = ipaddress.ip_address(ip_address)
            if adres.is_private or adres.is_loopback:
                return None
        except ValueError:
            return None

        try:
            url = f"https://ipwho.is/{ip_address}"
            with urllib.request.urlopen(url, timeout=8) as cevap:
                veri = json.loads(cevap.read())
        except Exception as exc:
            logger.warning("IP konumu alınamadı: %s", exc)
            return None

        if not veri.get("success"):
            return None

        return {
            "country": veri.get("country"),
            "city": veri.get("city"),
            "latitude": veri.get("lat"),
            "longitude": veri.get("lon"),
        }

    get_location_from_ip = ipten_konum_getir


IpService = IpServisi
