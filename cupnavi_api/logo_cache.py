import hashlib
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_LOGO_BYTES = 1_500_000
ALLOWED_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
CACHE_DIR = Path("/tmp/cupnavi-logo-cache")


def _public_https_url(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Logotypen måste komma från en publik HTTPS-adress.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("Logotypens värdnamn kunde inte verifieras.") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ValueError("Privata eller lokala bildadresser är inte tillåtna.")
    return parsed.geturl()


def cache_verified_logo(url: str, *, opener=urlopen) -> tuple[str, str]:
    safe_url = _public_https_url(url)
    request = Request(safe_url, headers={"User-Agent": "CupNavi/1.0 logo-cache", "Accept": "image/png,image/jpeg,image/webp,image/gif"})
    with opener(request, timeout=6) as response:
        content_type = str(response.headers.get_content_type() or "").lower()
        suffix = ALLOWED_TYPES.get(content_type)
        if not suffix:
            raise ValueError("Logotypkällan returnerade inte en tillåten bildtyp.")
        data = response.read(MAX_LOGO_BYTES + 1)
        if not data or len(data) > MAX_LOGO_BYTES:
            raise ValueError("Logotypbilden är tom eller för stor.")
    digest = hashlib.sha256(data).hexdigest()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(data)
    return digest, suffix
