import ipaddress
import os


def ip_anonimlestir(value: str | None) -> str | None:
    if not value:
        return None
    try:
        adres = ipaddress.ip_address(value)
    except ValueError:
        return None
    oneki = 24 if adres.version == 4 else 64
    return str(ipaddress.ip_network(f"{adres}/{oneki}", strict=False).network_address)


anonymize_ip = ip_anonimlestir


def istemci_ip_coz(request) -> str:
    if os.getenv("TRUST_PROXY_HEADERS", "false").lower() in {"1", "true", "yes", "on"}:
        iletilen = request.headers.get("x-forwarded-for", "")
        aday = iletilen.split(",")[0].strip()
        if ip_anonimlestir(aday) is not None:
            return aday
    return request.client.host if request.client else "127.0.0.1"


resolve_client_ip = istemci_ip_coz
