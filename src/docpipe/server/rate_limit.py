"""Bounded in-memory rate limiting for expensive API routes.

The middleware deliberately does not inspect request bodies: it runs before
route authentication, so buffering a body here would let unauthenticated
clients force arbitrary memory use.
"""

from __future__ import annotations

import ipaddress
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable, Sequence

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
        "/mcp",
        "/mcp/",
    }
)
_WINDOW_SECONDS = 60.0
_MAX_BUCKETS = 8192
_BUCKETS: OrderedDict[str, deque[float]] = OrderedDict()
_BUCKETS_LOCK = threading.Lock()
# Without buffering an unauthenticated body, preset-specific selection is not
# safe. Use the strictest configured preset limit for all expensive routes.
_REQUEST_LIMIT = min(PRESET_RATE_LIMITS.values())


def _client_key(
    request: Request,
    *,
    trusted_proxy_cidrs: Sequence[str] = (),
) -> str:
    """Use X-Forwarded-For only when the immediate TCP peer is a trusted proxy."""
    client = request.client
    if client is None or not client.host:
        return "unknown"
    peer_text = client.host
    try:
        peer = ipaddress.ip_address(peer_text)
    except ValueError:
        return peer_text

    try:
        trusted_networks = tuple(
            ipaddress.ip_network(cidr, strict=False) for cidr in trusted_proxy_cidrs
        )
    except ValueError:
        # Settings validation rejects this, but malformed direct callers should
        # never make the limiter trust a forwarding header.
        return peer_text

    def is_trusted(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        return any(
            address.version == network.version and address in network
            for network in trusted_networks
        )

    if not is_trusted(peer):
        return peer_text

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer_text
    try:
        chain = [ipaddress.ip_address(item.strip()) for item in forwarded.split(",")]
    except ValueError:
        return peer_text
    if not chain:
        return peer_text

    # The peer is trusted by configuration. Walk the XFF chain from the
    # nearest proxy toward the client, skipping only explicitly trusted hops.
    chain.append(peer)
    index = len(chain) - 1
    while index > 0 and is_trusted(chain[index]):
        index -= 1
    selected = chain[index]
    if is_trusted(selected):
        return peer_text
    return str(selected)


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
            limit = (
                settings.mcp_rate_limit_per_minute
                if request.url.path in {"/mcp", "/mcp/"}
                else _REQUEST_LIMIT
            )
            client_key = _client_key(
                request,
                trusted_proxy_cidrs=settings.rate_limit_trusted_proxy_cidrs,
            )
            detail = _check_limit(f"{client_key}:{request.url.path}", limit)
            if detail is not None:
                return JSONResponse(status_code=429, content={"detail": detail})

        return await call_next(request)
