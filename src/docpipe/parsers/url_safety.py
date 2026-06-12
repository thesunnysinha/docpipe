"""SSRF guards for parser URL sources."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from docpipe.config import get_settings
from docpipe.core.errors import ParseError


def is_private_host(hostname: str) -> bool:
    """Return True when hostname resolves to a non-global address."""
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        except OSError:
            return False
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or not ip.is_global)


def assert_safe_http_source(source: str) -> None:
    """Reject HTTP(S) sources that target private networks unless explicitly allowed."""
    if not source.startswith(("http://", "https://")):
        return
    parsed = urlparse(source)
    hostname = parsed.hostname
    if not hostname:
        raise ParseError(f"Invalid URL source: {source!r}")
    settings = get_settings()
    if settings.allow_private_urls:
        return
    if is_private_host(hostname):
        raise ParseError(
            "URL source resolves to a private network address. "
            "Set DOCPIPE_ALLOW_PRIVATE_URLS=true for trusted internal networks."
        )
