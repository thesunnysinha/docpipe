"""Operator configuration tests for the optional HTTP RAG cache."""

from __future__ import annotations

import pytest

from docpipe.bootstrap.server import _create_rag_cache
from docpipe.config.settings import DocpipeSettings
from docpipe.rag.cache_backends import InMemoryKVCache


def test_rag_cache_is_disabled_by_default() -> None:
    assert _create_rag_cache(DocpipeSettings()) is None


def test_memory_backend_uses_configured_capacity() -> None:
    cache = _create_rag_cache(DocpipeSettings(rag_cache_enabled=True, rag_cache_max_entries=7))

    assert isinstance(cache, InMemoryKVCache)
    assert cache._max_entries == 7


def test_redis_backend_requires_an_operator_url() -> None:
    settings = DocpipeSettings(rag_cache_enabled=True, rag_cache_backend="redis")

    with pytest.raises(RuntimeError, match="DOCPIPE_RAG_CACHE_REDIS_URL"):
        _create_rag_cache(settings)
