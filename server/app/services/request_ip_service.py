"""Extract real client IP from request with trusted proxy checks."""

from __future__ import annotations

from functools import lru_cache
import ipaddress

from starlette.requests import Request

from app.config import settings


@lru_cache(maxsize=1)
def _trusted_proxy_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    cidr_text = settings.TRUSTED_PROXY_CIDRS or ""
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for item in cidr_text.split(","):
        raw = item.strip()
        if not raw:
            continue
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            continue
    return networks


def _parse_ip(token: str | None) -> str | None:
    if not token:
        return None

    value = token.strip().strip('"').strip("'")
    if not value:
        return None

    if ";" in value:
        value = value.split(";", 1)[0].strip()
    if value.lower().startswith("for="):
        value = value.split("=", 1)[1].strip()

    if value.startswith("[") and "]" in value:
        value = value[1:value.index("]")]

    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass

    # Handle IPv4 with port, e.g. 1.2.3.4:1234
    if value.count(":") == 1 and "." in value:
        host = value.rsplit(":", 1)[0].strip()
        try:
            return str(ipaddress.ip_address(host))
        except ValueError:
            return None
    return None


def _is_trusted_proxy(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _trusted_proxy_networks())


def get_client_ip(request: Request) -> str | None:
    """Return best-effort real client IP.

    Security model:
    - If peer is not a trusted proxy, use peer IP directly.
    - Only when peer is trusted do we parse forwarding headers.
    """
    peer_ip = _parse_ip(request.client.host if request.client else None)
    if not peer_ip:
        return None

    if not settings.TRUST_PROXY_HEADERS or not _is_trusted_proxy(peer_ip):
        return peer_ip

    forwarded = request.headers.get("forwarded")
    if forwarded:
        for part in forwarded.split(","):
            candidate = _parse_ip(part)
            if candidate:
                return candidate

    xff = request.headers.get("x-forwarded-for")
    if xff:
        for part in xff.split(","):
            candidate = _parse_ip(part)
            if candidate:
                return candidate

    x_real_ip = _parse_ip(request.headers.get("x-real-ip"))
    if x_real_ip:
        return x_real_ip

    return peer_ip
