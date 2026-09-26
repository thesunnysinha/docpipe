"""Behavioral tests for bounded asynchronous cache backends."""

from __future__ import annotations

import pytest

from docpipe.rag.cache_backends import InMemoryKVCache, RedisKVCache


async def test_memory_cache_expires_and_evicts_least_recently_used() -> None:
    now = [0.0]
    cache = InMemoryKVCache(max_entries=2, clock=lambda: now[0])
    await cache.set("first", b"1", ttl_seconds=30)
    await cache.set("second", b"2", ttl_seconds=30)
    assert await cache.get("first") == b"1"  # first is now least-recently used
    await cache.set("third", b"3", ttl_seconds=30)

    assert await cache.get("second") is None
    assert await cache.get("first") == b"1"
    now[0] = 31.0
    assert await cache.get("first") is None
    assert await cache.get("third") is None


async def test_memory_cache_copies_values_and_clears_on_close() -> None:
    cache = InMemoryKVCache(max_entries=1)
    mutable = bytearray(b"payload")
    await cache.set("key", mutable, ttl_seconds=5)
    mutable[:] = b"changed"

    assert await cache.get("key") == b"payload"
    await cache.close()
    assert await cache.get("key") is None


async def test_redis_cache_uses_ttl_and_closes_client() -> None:
    class FakeRedis:
        saved: tuple[str, bytes, int] | None = None
        closed = False

        async def get(self, key: str) -> bytes | None:
            return self.saved[1] if self.saved and self.saved[0] == key else None

        async def set(self, key: str, value: bytes, *, ex: int) -> None:
            self.saved = (key, value, ex)

        async def aclose(self) -> None:
            self.closed = True

    client = FakeRedis()
    cache = RedisKVCache(client)
    await cache.set("opaque", b"value", ttl_seconds=42)

    assert await cache.get("opaque") == b"value"
    assert client.saved == ("docpipe:rag:opaque", b"value", 42)
    await cache.close()
    assert client.closed


async def test_backends_reject_unbounded_lifetime() -> None:
    cache = InMemoryKVCache()
    with pytest.raises(ValueError, match="ttl_seconds"):
        await cache.set("key", b"value", ttl_seconds=0)
