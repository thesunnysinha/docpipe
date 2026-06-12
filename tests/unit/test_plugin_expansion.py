"""Tests for plugin expansion (chunkers, rerankers, parsers router, evaluators)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from docpipe.chunkers.recursive_chunker import RecursiveChunker
from docpipe.core.errors import ChunkerNotFoundError, RerankerNotFoundError
from docpipe.core.types import (
    EvalConfig,
    EvalMetrics,
    EvalQuestion,
    IngestionConfig,
    RAGChunk,
    RAGConfig,
)
from docpipe.eval.builtin_evaluator import BuiltinEvaluator
from docpipe.eval.pipeline import EvalPipeline
from docpipe.parsers.router import resolve_parser
from docpipe.registry.registry import PluginRegistry
from docpipe.rerankers.flashrank_reranker import FlashRankReranker
from tests.conftest import MockParser


def test_registry_chunkers_and_rerankers():
    registry = PluginRegistry.get()
    registry.register_chunker("recursive", RecursiveChunker)
    registry.register_reranker("flashrank", FlashRankReranker)

    assert "recursive" in registry.list_chunkers()
    assert "flashrank" in registry.list_rerankers()
    info = registry.chunker_info("recursive")
    assert info["name"] == "recursive"
    assert registry.all_plugins()["chunkers"]["recursive"]["name"] == "recursive"


def test_get_unknown_chunker_raises():
    registry = PluginRegistry.get()
    with pytest.raises(ChunkerNotFoundError):
        registry.get_chunker("missing")


def test_get_unknown_reranker_raises():
    registry = PluginRegistry.get()
    with pytest.raises(RerankerNotFoundError):
        registry.get_reranker("missing")


def test_resolve_parser_auto_prefers_available():
    registry = PluginRegistry.get()
    registry.register_parser("markitdown", MockParser)
    name = resolve_parser("auto", tier="fast", source="report.pdf")
    assert name == "markitdown"


def test_builtin_evaluator_registers():
    registry = PluginRegistry.get()
    registry.register_evaluator("builtin", BuiltinEvaluator)
    ev = registry.get_evaluator("builtin")
    assert ev.name == "builtin"


@patch("docpipe.eval.builtin_evaluator.RAGPipeline")
def test_eval_pipeline_delegates_to_evaluator(mock_rag_cls):
    mock_rag = MagicMock()
    mock_rag.query.return_value = MagicMock(
        answer="42",
        chunks=[],
        sources=[],
    )
    mock_rag._llm = MagicMock()
    mock_rag_cls.return_value = mock_rag

    registry = PluginRegistry.get()
    registry.register_evaluator("builtin", BuiltinEvaluator)

    cfg = EvalConfig(
        rag_config=RAGConfig(
            connection_string="postgresql://x",
            table_name="docs",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            system_prompt="ctx={context} q={question}",
        ),
        questions=[EvalQuestion(question="What?", expected_answer="42")],
        metrics=["answer_similarity"],
    )
    with patch.object(BuiltinEvaluator, "_llm_judge_similarity", return_value=1.0):
        result = EvalPipeline(cfg).run()
    assert result.num_questions == 1
    assert isinstance(result.metrics, EvalMetrics)


def test_recursive_chunker_splits_documents():
    from langchain_core.documents import Document

    config = IngestionConfig(
        connection_string="postgresql://x",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )
    chunker = RecursiveChunker(config)
    docs = [Document(page_content="word " * 500, metadata={"source": "a.txt"})]
    chunks = chunker.split_documents(docs)
    assert len(chunks) > 1


def test_flashrank_reranker_top_n():
    mock_flashrank = MagicMock()
    mock_ranker = MagicMock()
    mock_ranker.rerank.return_value = [{"index": 0}, {"index": 1}]
    mock_flashrank.Ranker.return_value = mock_ranker
    mock_flashrank.RerankRequest = MagicMock(
        side_effect=lambda query, passages: {"query": query, "passages": passages}
    )
    chunks = [
        RAGChunk(content="a", score=0.5, source="s"),
        RAGChunk(content="b", score=0.4, source="s"),
    ]
    with patch.dict(sys.modules, {"flashrank": mock_flashrank}):
        reranker = FlashRankReranker()
        ranked = reranker.rerank("query", chunks, top_n=1)
    assert len(ranked) == 1
    assert ranked[0].content == "a"
