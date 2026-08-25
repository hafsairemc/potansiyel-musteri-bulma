import ipaddress
import re
from urllib.parse import urlparse


class AlanAdiGirisServisi:
    _etiket_kalibi = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
    _label = _etiket_kalibi

    @classmethod
    def normallestir(cls, value: str | None) -> str | None:
        aday = (value or "").strip().lower()
        if not aday:
            return None

        ayristirilmis = urlparse(aday if "://" in aday else f"https://{aday}")
        if ayristirilmis.username or ayristirilmis.password or ayristirilmis.port:
            raise ValueError("Geçerli bir şirket domaini girin")

        alan_adi = (ayristirilmis.hostname or "").removeprefix("www.").rstrip(".")
        try:
            alan_adi = alan_adi.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("Geçerli bir şirket domaini girin") from exc

        if len(alan_adi) > 253 or "." not in alan_adi:
            raise ValueError("Geçerli bir şirket domaini girin")

        try:
            ipaddress.ip_address(alan_adi)
        except ValueError:
            pass
        else:
            raise ValueError("IP adresi yerine şirket domaini girin")

        if not all(cls._etiket_kalibi.fullmatch(etiket) for etiket in alan_adi.split(".")):
            raise ValueError("Geçerli bir şirket domaini girin")

        return alan_adi

    normalize = normallestir


DomainInputService = AlanAdiGirisServisi
