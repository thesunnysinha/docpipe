"""Legacy parser URL-safety facade over the source transport policy."""

from __future__ import annotations

import socket
from typing import cast

from docpipe.config import get_settings
from docpipe.core.errors import ParseError
from docpipe.plugins.errors import SourceError
from docpipe.sources.http_security import (
    HttpSecurityPolicy,
    inspect_http_url,
    validate_resolved_addresses,
)


def is_private_host(hostname: str) -> bool:
    """Return whether any resolved address violates the public-network policy."""
    try:
        answers = socket.getaddrinfo(hostname, 443, 0, socket.SOCK_STREAM)
        validate_resolved_addresses(
            (cast(str, answer[4][0]) for answer in answers),
            HttpSecurityPolicy(allow_private=False),
        )
    except (OSError, SourceError):
        return True
    return False


def assert_safe_http_source(source: str) -> None:
    """Reject HTTP(S) sources that target private networks unless explicitly allowed."""
    if not source.startswith(("http://", "https://")):
        return
    settings = get_settings()
    policy = HttpSecurityPolicy(allow_private=settings.allow_private_urls)
    try:
        parsed = inspect_http_url(source, policy)
        assert parsed.hostname is not None
        if not settings.allow_private_urls and is_private_host(parsed.hostname):
            raise ParseError(
                "URL source resolves to a private network address. "
                "Set DOCPIPE_ALLOW_PRIVATE_URLS=true for trusted internal networks."
            )
    except SourceError as error:
        raise ParseError(
            "URL source resolves to a private network address or violates "
            "the configured source network policy"
        ) from error
