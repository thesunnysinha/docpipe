"""Stable RAG SDK model and provider configuration regressions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk, RAGConfig, RAGResult
from docpipe.plugins.loader import PluginLoader
from docpipe.rag.pipeline import RAGPipeline


def _config(**overrides: object) -> RAGConfig:
    values: dict[str, object] = {
        "connection_string": "postgresql://test/db",
        "table_name": "documents",
        "embedding_provider": "openai",
        "embedding_model": "model",
        "llm_provider": "openai",
        "llm_model": "model",
        "system_prompt": "Use {context} for {question}",
    }
    values.update(overrides)
    return RAGConfig.model_validate(values)


def test_rag_config_defaults() -> None:
    config = _config()
    assert config.strategy == "naive"
    assert config.top_k == 5
    assert config.multi_query_count == 3
    assert config.parent_window_size == 3
    assert config.hybrid_bm25_weight == 0.5
    assert config.reranker == "none"
    assert config.max_chunks_per_source == 2
    assert config.output_model is None


def test_unknown_embedding_provider_raises_before_query() -> None:
    with (
        patch.object(RAGPipeline, "_create_llm", return_value=MagicMock()),
        pytest.raises(ConfigurationError, match="Unknown embedding provider"),
    ):
        RAGPipeline(_config(embedding_provider="nonexistent"))


def test_unknown_llm_provider_raises_before_query() -> None:
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=MagicMock()),
        pytest.raises(ConfigurationError, match="Unknown LLM provider"),
    ):
        RAGPipeline(_config(llm_provider="nonexistent"))


def test_result_serializes_public_fields_but_not_structured_value() -> None:
    result = RAGResult(
        query="q",
        answer="a",
        strategy="naive",
        chunks=[RAGChunk(content="text", score=0.9, source="a.pdf")],
        sources=["a.pdf"],
        timing_seconds=0.5,
        structured={"private": "value"},
    )
    assert result.model_dump()["sources"] == ["a.pdf"]
    assert "structured" not in result.model_dump()


def test_unknown_strategy_fails_before_plugin_loading() -> None:
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=MagicMock()),
        patch.object(RAGPipeline, "_create_llm", return_value=MagicMock()),
        patch.object(PluginLoader, "load") as loader,
    ):
        pipeline = RAGPipeline(_config())
        pipeline._config.strategy = "missing"  # type: ignore[assignment]
        with pytest.raises(RAGError, match="Unknown strategy 'missing'"):
            pipeline.query("question")
        loader.assert_not_called()


def test_hyde_requires_prompt_before_plugin_loading() -> None:
    with (
        patch.object(RAGPipeline, "_create_embeddings", return_value=MagicMock()),
        patch.object(RAGPipeline, "_create_llm", return_value=MagicMock()),
        patch.object(PluginLoader, "load") as loader,
        pytest.raises(ConfigurationError, match="hyde_prompt"),
    ):
        RAGPipeline(_config(strategy="hyde")).query("question")
    loader.assert_not_called()
