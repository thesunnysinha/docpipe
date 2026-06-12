"""Optional in-memory parse result cache keyed by source."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from docpipe.core.types import ParsedDocument

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(source: str, parser: str) -> str:
    digest = hashlib.sha256(f"{parser}:{source}".encode()).hexdigest()
    return digest


def get_cached_parse(source: str, parser: str, *, ttl_seconds: int) -> ParsedDocument | None:
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
    if ttl_seconds <= 0:
        return
    key = _cache_key(source, parser)
    _CACHE[key] = (time.monotonic() + ttl_seconds, document.model_dump())
