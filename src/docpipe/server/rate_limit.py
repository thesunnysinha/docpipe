"""In-memory preset-aware rate limiting for expensive API routes."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response
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
_buckets: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "anonymous")
    tenant = request.headers.get("X-Docpipe-Tenant-Id", "")
    return f"{tenant}:{auth[:32]}"


def _extract_preset(body: bytes) -> str:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return "balanced"
    preset = data.get("preset")
    return str(preset) if preset else "balanced"


def _check_limit(key: str, limit: int) -> None:
    now = time.monotonic()
    window_start = now - _WINDOW_SECONDS
    hits = [t for t in _buckets[key] if t >= window_start]
    if len(hits) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({limit} requests per minute for this preset).",
        )
    hits.append(now)
    _buckets[key] = hits


class PresetRateLimitMiddleware(BaseHTTPMiddleware):
    """Limit POST throughput per client and runtime preset."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        from docpipe.config import get_settings

        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        if request.method != "POST" or request.url.path not in _PRESET_PATHS:
            return await call_next(request)

        body = await request.body()
        preset = _extract_preset(body)
        limit = PRESET_RATE_LIMITS.get(preset, PRESET_RATE_LIMITS["balanced"])
        _check_limit(f"{_client_key(request)}:{preset}:{request.url.path}", limit)

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, receive)
        return await call_next(request)
