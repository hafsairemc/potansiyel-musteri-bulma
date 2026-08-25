import ipaddress
import socket
from urllib.parse import urlparse


def guvenli_kamusal_url(value: str) -> str | None:
    aday = value.strip()
    if not aday:
        return None
    if not aday.startswith(("http://", "https://")):
        aday = f"https://{aday}"

    ayristirilmis = urlparse(aday)
    if ayristirilmis.scheme not in {"http", "https"} or not ayristirilmis.hostname or ayristirilmis.username or ayristirilmis.password:
        return None

    try:
        adresler = socket.getaddrinfo(ayristirilmis.hostname, ayristirilmis.port or (443 if ayristirilmis.scheme == "https" else 80))
        if any(not ipaddress.ip_address(oge[4][0]).is_global for oge in adresler):
            return None
    except (OSError, ValueError):
        return None

    return aday


safe_public_url = guvenli_kamusal_url
