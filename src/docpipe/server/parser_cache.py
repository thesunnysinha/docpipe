"""Optional process-local TTL cache for parsed documents.

Entries are keyed by a SHA-256 digest of parser name and source, and hold a
serialized document until its monotonic-clock expiry. A non-positive TTL
disables reads and writes. This module-level cache is neither bounded nor
shared across workers; it is not a distributed production cache.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from docpipe.core.types import ParsedDocument

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(source: str, parser: str) -> str:
    """Return a stable opaque key that separates parsers for the same source."""
    digest = hashlib.sha256(f"{parser}:{source}".encode()).hexdigest()
    return digest


def get_cached_parse(source: str, parser: str, *, ttl_seconds: int) -> ParsedDocument | None:
    """Return an unexpired cached parse, or ``None`` when caching is disabled/missed.

    The payload is revalidated into a new ``ParsedDocument`` on each hit so
    callers do not receive the mutable object retained by the cache.
    """
    if ttl_seconds <= 0:
        return None
    key = _cache_key(source, parser)
    entry = _CACHE.get(key)
    if entry is None:
        return None
    expires_at, payload = entry
    if time.monotonic() > expires_at:
        _CACHE.pop(key, None)
        return None
    return ParsedDocument.model_validate(payload)


def store_cached_parse(
    source: str,
    parser: str,
    document: ParsedDocument,
    *,
    ttl_seconds: int,
) -> None:
    """Store a serialized parse result until the supplied TTL expires.

    A non-positive TTL is a no-op. Expired entries are removed lazily when
    their key is next read; no background cleanup task is created.
    """
    if ttl_seconds <= 0:
        return
    key = _cache_key(source, parser)
    _CACHE[key] = (time.monotonic() + ttl_seconds, document.model_dump())
