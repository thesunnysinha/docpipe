"""Pipeline integration tests for injected exact-key response caching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from docpipe.core.types import RAGChunk, RAGConfig, RAGResult, TokenUsage
from docpipe.rag.cache import cache_key
from docpipe.rag.pipeline import RAGPipeline


def _config(**overrides: object) -> RAGConfig:
    values: dict[str, object] = {
        "connection_string": "postgresql://user:secret@db/docpipe",
        "table_name": "documents",
        "embedding_provider": "openai",
        "embedding_model": "embed-model",
        "embedding_api_key": "embedding-secret",
        "llm_provider": "openai",
        "llm_model": "answer-model",
        "llm_api_key": "llm-secret",
        "cache_enabled": True,
    }
    values.update(overrides)
    return RAGConfig.model_validate(values)


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.error: Exception | None = None
        self.writes: list[tuple[str, bytes, int]] = []

    async def get(self, key: str) -> bytes | None:
        if self.error:
            raise self.error
        return self.values.get(key)

    async def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        if self.error:
            raise self.error
        self.values[key] = value
        self.writes.append((key, value, ttl_seconds))

    async def close(self) -> None:
        self.values.clear()


def _pipeline(cache: FakeCache, *, max_bytes: int = 4096) -> RAGPipeline:
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=MagicMock()),
        patch.object(RAGPipeline, "_create_llm", return_value=MagicMock()),
    ):
        return RAGPipeline(
            _config(),
            cache_backend=cache,
            cache_tenant_scope="tenant-a",
            cache_ttl_seconds=45,
            cache_max_payload_bytes=max_bytes,
        )


def _result() -> RAGResult:
    return RAGResult(
        query="exact question",
        answer="cached answer",
        strategy="naive",
        chunks=[RAGChunk(content="evidence", score=0.9, source="source.pdf")],
        sources=["source.pdf"],
        timing_seconds=0.4,
        usage=TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120),
    )


async def test_injected_cache_round_trips_result_with_bounded_ttl() -> None:
    backend = FakeCache()
    pipeline = _pipeline(backend)
    result = _result()

    await pipeline._kv_cache_store("exact question", result)
    cached = await pipeline._kv_cache_lookup("exact question")

    assert cached == result
    assert len(backend.writes) == 1
    key, payload, ttl = backend.writes[0]
    assert key not in payload.decode()
    assert b"llm-secret" not in payload
    assert b"embedding-secret" not in payload
    assert ttl == 45


async def test_cache_hit_reports_current_lookup_latency_without_old_usage() -> None:
    backend = FakeCache()
    pipeline = _pipeline(backend)
    await pipeline._kv_cache_store("exact question", _result())

    cached = await pipeline._query_with_runtime("exact question", object())  # type: ignore[arg-type]

    assert cached.answer == "cached answer"
    assert cached.timing_seconds < 0.4
    assert cached.usage is None
    assert pipeline.last_usage is None


async def test_backend_outage_is_a_cache_miss_and_write_is_best_effort() -> None:
    backend = FakeCache()
    backend.error = OSError("redis is unavailable")
    pipeline = _pipeline(backend)

    assert await pipeline._kv_cache_lookup("exact question") is None
    await pipeline._kv_cache_store("exact question", _result())


async def test_oversized_cached_values_are_ignored_and_not_written() -> None:
    backend = FakeCache()
    pipeline = _pipeline(backend, max_bytes=10)

    await pipeline._kv_cache_store("exact question", _result())
    assert backend.writes == []

    key = cache_key(pipeline._config, "exact question", tenant_scope="tenant-a")
    backend.values[key] = b"x" * 11
    assert await pipeline._kv_cache_lookup("exact question") is None
