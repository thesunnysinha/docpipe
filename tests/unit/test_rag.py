"""Unit tests for RAGPipeline — all external calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk, RAGConfig, RAGResult
from docpipe.rag.pipeline import RAGPipeline


def _make_config(**overrides: object) -> RAGConfig:
    defaults = dict(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    defaults.update(overrides)
    return RAGConfig(**defaults)  # type: ignore[arg-type]


def _mock_doc(content: str = "chunk text", source: str = "doc.pdf", page: int = 1) -> MagicMock:
    doc = MagicMock()
    doc.page_content = content
    doc.metadata = {"source": source, "page": page}
    return doc


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


def test_rag_config_defaults() -> None:
    config = _make_config()
    assert config.strategy == "naive"
    assert config.top_k == 5
    assert config.multi_query_count == 3
    assert config.parent_window_size == 3
    assert config.hybrid_bm25_weight == 0.5
    assert config.reranker == "none"
    assert config.output_model is None


# ---------------------------------------------------------------------------
# Unknown provider errors raised at __init__
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_llm")
def test_unknown_embedding_provider_raises(mock_llm: MagicMock) -> None:
    mock_llm.return_value = MagicMock()
    config = _make_config(embedding_provider="nonexistent")
    with pytest.raises(ConfigurationError, match="Unknown embedding provider"):
        RAGPipeline(config)


@patch.object(RAGPipeline, "_create_embeddings")
def test_unknown_llm_provider_raises(mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    config = _make_config(llm_provider="nonexistent")
    with pytest.raises(ConfigurationError, match="Unknown LLM provider"):
        RAGPipeline(config)


# ---------------------------------------------------------------------------
# Invalid strategy
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_invalid_strategy_raises(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    mock_llm.return_value = MagicMock()

    config = _make_config()
    pipeline = RAGPipeline(config)
    pipeline._config.strategy = "bad_strategy"  # type: ignore[assignment]
    with pytest.raises(RAGError, match="Unknown strategy"):
        pipeline.query("test")


# ---------------------------------------------------------------------------
# Naive strategy
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_naive_query(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="The answer is 42.")
    mock_llm.return_value = llm

    pipeline = RAGPipeline(_make_config(strategy="naive"))

    vs = MagicMock()
    doc = _mock_doc("Some relevant text.", "report.pdf", 3)
    vs.similarity_search_with_score.return_value = [(doc, 0.91)]

    with patch.object(pipeline, "_get_vectorstore", return_value=vs):
        result = pipeline.query("What is the answer?")

    assert result.answer == "The answer is 42."
    assert result.strategy == "naive"
    assert len(result.chunks) == 1
    assert result.chunks[0].source == "report.pdf"
    assert result.chunks[0].score == pytest.approx(0.91)
    assert result.sources == ["report.pdf"]
    assert result.timing_seconds > 0
    vs.similarity_search_with_score.assert_called_once_with("What is the answer?", k=5)


# ---------------------------------------------------------------------------
# Sources deduplication
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_sources_deduplicated(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="Answer.")
    mock_llm.return_value = llm

    pipeline = RAGPipeline(_make_config())
    vs = MagicMock()
    doc1 = _mock_doc("chunk 1", "same.pdf", 1)
    doc2 = _mock_doc("chunk 2", "same.pdf", 2)
    vs.similarity_search_with_score.return_value = [(doc1, 0.9), (doc2, 0.8)]

    with patch.object(pipeline, "_get_vectorstore", return_value=vs):
        result = pipeline.query("question")

    assert result.sources == ["same.pdf"]


# ---------------------------------------------------------------------------
# HyDE strategy
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_hyde_query_uses_hypothetical_doc(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    llm.invoke.side_effect = [
        MagicMock(content="Hypothetical passage about revenue."),
        MagicMock(content="Revenue was $5M."),
    ]
    mock_llm.return_value = llm

    pipeline = RAGPipeline(_make_config(strategy="hyde"))
    vs = MagicMock()
    doc = _mock_doc("Revenue details.", "finance.pdf", 5)
    vs.similarity_search_with_score.return_value = [(doc, 0.95)]

    with patch.object(pipeline, "_get_vectorstore", return_value=vs):
        result = pipeline.query("What was the revenue?")

    # Search must use the hypothetical doc, not the original question
    vs.similarity_search_with_score.assert_called_once_with(
        "Hypothetical passage about revenue.", k=5
    )
    assert result.answer == "Revenue was $5M."
    assert result.metadata.get("hypothetical_doc") == "Hypothetical passage about revenue."


# ---------------------------------------------------------------------------
# Multi-query strategy
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_multi_query_deduplicates(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    llm.invoke.side_effect = [
        MagicMock(content="variant 1\nvariant 2\nvariant 3"),
        MagicMock(content="Final answer."),
    ]
    mock_llm.return_value = llm

    pipeline = RAGPipeline(_make_config(strategy="multi_query", multi_query_count=3))
    vs = MagicMock()
    # Same doc returned for every variant → should deduplicate to 1 chunk
    same_doc = _mock_doc("unique content", "file.pdf", 1)
    vs.similarity_search_with_score.return_value = [(same_doc, 0.88)]

    with patch.object(pipeline, "_get_vectorstore", return_value=vs):
        result = pipeline.query("original question")

    assert len(result.chunks) == 1
    assert "query_variants" in result.metadata
    assert result.answer == "Final answer."


# ---------------------------------------------------------------------------
# Parent-document strategy
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_parent_document_expands_context(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="Expanded answer.")
    mock_llm.return_value = llm

    pipeline = RAGPipeline(_make_config(strategy="parent_document", parent_window_size=2))
    vs = MagicMock()
    seed = _mock_doc("seed chunk", "report.pdf", 1)
    extra = _mock_doc("extra chunk from same source", "report.pdf", 2)
    # First call: seed retrieval; second call: source-filtered expansion
    vs.similarity_search_with_score.side_effect = [
        [(seed, 0.9)],
        [(extra, 0.7)],
    ]

    with patch.object(pipeline, "_get_vectorstore", return_value=vs):
        result = pipeline.query("question")

    assert len(result.chunks) == 2
    # Second call must use filter on source
    second_call_kwargs = vs.similarity_search_with_score.call_args_list[1][1]
    assert second_call_kwargs.get("filter") == {"source": "report.pdf"}


# ---------------------------------------------------------------------------
# Hybrid strategy — missing dependency error
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_hybrid_missing_dep_raises(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    mock_llm.return_value = MagicMock()

    import sys

    pipeline = RAGPipeline(_make_config(strategy="hybrid"))
    vs = MagicMock()
    vs.similarity_search_with_score.return_value = [(_mock_doc(), 0.8)]

    with patch.object(pipeline, "_get_vectorstore", return_value=vs):
        with patch.dict(sys.modules, {"langchain_community": None,
                                      "langchain_community.retrievers": None}):
            with pytest.raises(RAGError, match="langchain-community"):
                pipeline.query("test")


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_structured_rag_output(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    from pydantic import BaseModel as PydanticModel

    class Invoice(PydanticModel):
        total: float
        currency: str

    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    structured_llm = MagicMock()
    invoice_obj = Invoice(total=4250.0, currency="USD")
    structured_llm.invoke.return_value = invoice_obj
    llm.with_structured_output.return_value = structured_llm
    mock_llm.return_value = llm

    pipeline = RAGPipeline(_make_config(output_model=Invoice))
    vs = MagicMock()
    vs.similarity_search_with_score.return_value = [(_mock_doc(), 0.9)]

    with patch.object(pipeline, "_get_vectorstore", return_value=vs):
        result = pipeline.query("What is the total?")

    llm.with_structured_output.assert_called_once_with(Invoice)
    assert result.structured is invoice_obj
    assert "4250" in result.answer


# ---------------------------------------------------------------------------
# RAGResult fields
# ---------------------------------------------------------------------------


def test_rag_result_is_pydantic() -> None:
    chunk = RAGChunk(content="text", score=0.9, source="a.pdf")
    result = RAGResult(
        query="q",
        answer="a",
        strategy="naive",
        chunks=[chunk],
        sources=["a.pdf"],
        timing_seconds=0.5,
    )
    data = result.model_dump()
    assert data["query"] == "q"
    assert data["sources"] == ["a.pdf"]
    # structured is excluded from serialization
    assert "structured" not in data
