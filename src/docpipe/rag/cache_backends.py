"""Bounded asynchronous key-value backends for RAG response caching."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Protocol


class AsyncKVCache(Protocol):
    """Minimal async byte-value cache contract used by the RAG pipeline."""

    async def get(self, key: str) -> bytes | None:
        """Return a value, or ``None`` when it is absent or expired."""

    async def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        """Store a value for a finite lifetime."""

    async def close(self) -> None:
        """Release backend resources owned by this cache instance."""


class InMemoryKVCache:
    """Process-local bounded KV cache for development and single-worker use.

    This backend is intentionally not described as durable or distributed.
    Eviction is least-recently-used, and all entries have an explicit expiry.
    """

    def __init__(self, *, max_entries: int = 10_000, clock: Callable[[], float] = time.monotonic):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> bytes | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= self._clock():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return value

    async def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        async with self._lock:
            self._entries[key] = (self._clock() + ttl_seconds, bytes(value))
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    async def close(self) -> None:
        """Clear cached answers when the owning application shuts down."""
        async with self._lock:
            self._entries.clear()


class RedisKVCache:
    """Optional Redis-backed TTL KV cache; Redis remains operator-managed.

    Construction is lazy with respect to network access so a temporary Redis
    outage does not prevent the API from starting. Call ``close`` at shutdown.
    """

    def __init__(self, client: object) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str, *, socket_timeout_seconds: float = 1.0) -> RedisKVCache:
        """Create a client from the optional ``redis`` extra without connecting."""
        try:
            from redis.asyncio import Redis
        except ImportError as exc:
            raise RuntimeError(
                "Redis RAG caching requires the optional dependency; "
                "install docpipe-sdk[rag-redis]."
            ) from exc
        client = Redis.from_url(
            url,
            socket_connect_timeout=socket_timeout_seconds,
            socket_timeout=socket_timeout_seconds,
            decode_responses=False,
        )
        return cls(client)

    async def get(self, key: str) -> bytes | None:
        value = await self._client.get(_redis_key(key))  # type: ignore[attr-defined]
        return bytes(value) if value is not None else None

    async def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        await self._client.set(  # type: ignore[attr-defined]
            _redis_key(key), value, ex=ttl_seconds
        )

    async def close(self) -> None:
        """Close the async Redis connection pool."""
        close = getattr(self._client, "aclose", None) or self._client.close  # type: ignore[attr-defined]
        result = close()
        if asyncio.iscoroutine(result):
            await result


def _redis_key(key: str) -> str:
    """Add a stable namespace without retaining caller-controlled key text."""
    return f"docpipe:rag:{key}"
