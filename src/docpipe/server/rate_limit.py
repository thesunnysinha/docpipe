"""Bounded in-memory rate limiting for expensive API routes.

The middleware deliberately does not inspect request bodies: it runs before
route authentication, so buffering a body here would let unauthenticated
clients force arbitrary memory use.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from docpipe.profiles.catalog import PRESET_RATE_LIMITS

_PRESET_PATHS = frozenset(
    {
        "/ingest",
        "/ingest/stream",
        "/parse",
        "/rag/query",
        "/rag/stream",
        "/run",
    }
)
_WINDOW_SECONDS = 60.0
_MAX_BUCKETS = 8192
_BUCKETS: OrderedDict[str, deque[float]] = OrderedDict()
_BUCKETS_LOCK = threading.Lock()
# Without buffering an unauthenticated body, preset-specific selection is not
# safe. Use the strictest configured preset limit for all expensive routes.
_REQUEST_LIMIT = min(PRESET_RATE_LIMITS.values())


def _client_key(request: Request) -> str:
    """Use the transport peer, never attacker-controlled identity headers."""
    client = request.client
    return client.host if client is not None and client.host else "unknown"


def _check_limit(key: str, limit: int) -> str | None:
    """Enforce a sliding window while bounding keys and per-key timestamps."""
    now = time.monotonic()
    window_start = now - _WINDOW_SECONDS
    with _BUCKETS_LOCK:
        expired_keys = [
            bucket_key
            for bucket_key, hits in _BUCKETS.items()
            if not hits or hits[-1] < window_start
        ]
        for bucket_key in expired_keys:
            del _BUCKETS[bucket_key]

        hits = _BUCKETS.get(key)
        if hits is None:
            if len(_BUCKETS) >= _MAX_BUCKETS:
                return "Rate limit capacity exceeded."
            hits = deque()
            _BUCKETS[key] = hits
        else:
            _BUCKETS.move_to_end(key)

        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= limit:
            return "Rate limit exceeded (requests per minute for expensive operations)."
        hits.append(now)
        return None


class PresetRateLimitMiddleware(BaseHTTPMiddleware):
    """Limit expensive POST throughput per transport client and route."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = request.app.state.docpipe_runtime.settings
        if not settings.rate_limit_enabled:
            return await call_next(request)

        if request.method == "POST" and request.url.path in _PRESET_PATHS:
            detail = _check_limit(f"{_client_key(request)}:{request.url.path}", _REQUEST_LIMIT)
            if detail is not None:
                return JSONResponse(status_code=429, content={"detail": detail})

        return await call_next(request)
