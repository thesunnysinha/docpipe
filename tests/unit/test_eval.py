"""Unit tests for EvalPipeline — all external calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.types import EvalConfig, EvalQuestion, RAGConfig, RAGChunk, RAGResult
from docpipe.rag.pipeline import RAGPipeline


def _make_rag_config() -> RAGConfig:
    return RAGConfig(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o",
    )


def _make_eval_config(
    questions: list[EvalQuestion] | None = None,
    metrics: list[str] | None = None,
) -> EvalConfig:
    if questions is None:
        questions = [
            EvalQuestion(
                question="What is X?",
                expected_answer="X is 42.",
                expected_sources=["report.pdf"],
            )
        ]
    return EvalConfig(
        rag_config=_make_rag_config(),
        questions=questions,
        metrics=metrics or ["hit_rate", "answer_similarity"],
    )


def _fake_rag_result(
    answer: str = "X is 42.",
    sources: list[str] | None = None,
) -> RAGResult:
    chunk = RAGChunk(content="some text", score=0.9, source=(sources or ["report.pdf"])[0])
    return RAGResult(
        query="What is X?",
        answer=answer,
        strategy="naive",
        chunks=[chunk],
        sources=sources or ["report.pdf"],
        timing_seconds=0.1,
    )


# ---------------------------------------------------------------------------
# EvalConfig defaults
# ---------------------------------------------------------------------------


def test_eval_config_defaults() -> None:
    cfg = EvalConfig(rag_config=_make_rag_config(), questions=[])
    assert cfg.metrics == ["hit_rate", "answer_similarity"]


# ---------------------------------------------------------------------------
# hit_rate metric
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_hit_rate_when_source_retrieved(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    mock_llm.return_value = MagicMock()

    from docpipe.eval.pipeline import EvalPipeline

    cfg = _make_eval_config(metrics=["hit_rate"])
    runner = EvalPipeline(cfg)

    with patch.object(runner._rag, "query", return_value=_fake_rag_result(sources=["report.pdf"])):
        result = runner.run()

    assert result.metrics.hit_rate == pytest.approx(1.0)


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_hit_rate_when_source_not_retrieved(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    mock_llm.return_value = MagicMock()

    from docpipe.eval.pipeline import EvalPipeline

    cfg = _make_eval_config(metrics=["hit_rate"])
    runner = EvalPipeline(cfg)

    with patch.object(runner._rag, "query", return_value=_fake_rag_result(sources=["other.pdf"])):
        result = runner.run()

    assert result.metrics.hit_rate == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# MRR metric
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_mrr_first_position(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    mock_llm.return_value = MagicMock()

    from docpipe.eval.pipeline import EvalPipeline

    cfg = _make_eval_config(metrics=["mrr"])
    runner = EvalPipeline(cfg)
    fake = _fake_rag_result(sources=["report.pdf", "other.pdf"])

    with patch.object(runner._rag, "query", return_value=fake):
        result = runner.run()

    assert result.metrics.mrr == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# answer_similarity (LLM judge)
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_answer_similarity_llm_judge(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="0.85")
    mock_llm.return_value = llm

    from docpipe.eval.pipeline import EvalPipeline

    cfg = _make_eval_config(metrics=["answer_similarity"])
    runner = EvalPipeline(cfg)

    with patch.object(runner._rag, "query", return_value=_fake_rag_result()):
        result = runner.run()

    assert result.metrics.answer_similarity == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# num_questions and timing
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_eval_result_metadata(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="1.0")
    mock_llm.return_value = llm

    from docpipe.eval.pipeline import EvalPipeline

    questions = [
        EvalQuestion(question="Q1?", expected_answer="A1", expected_sources=["f.pdf"]),
        EvalQuestion(question="Q2?", expected_answer="A2", expected_sources=["f.pdf"]),
    ]
    cfg = _make_eval_config(questions=questions, metrics=["hit_rate"])
    runner = EvalPipeline(cfg)

    with patch.object(runner._rag, "query", return_value=_fake_rag_result(sources=["f.pdf"])):
        result = runner.run()

    assert result.num_questions == 2
    assert result.timing_seconds > 0
    assert len(result.metrics.per_question) == 2


# ---------------------------------------------------------------------------
# Metrics not in requested list are None
# ---------------------------------------------------------------------------


@patch.object(RAGPipeline, "_create_embeddings")
@patch.object(RAGPipeline, "_create_llm")
def test_unselected_metrics_are_none(mock_llm: MagicMock, mock_emb: MagicMock) -> None:
    mock_emb.return_value = MagicMock()
    mock_llm.return_value = MagicMock()

    from docpipe.eval.pipeline import EvalPipeline

    cfg = _make_eval_config(metrics=["hit_rate"])
    runner = EvalPipeline(cfg)

    with patch.object(runner._rag, "query", return_value=_fake_rag_result()):
        result = runner.run()

    assert result.metrics.mrr is None
    assert result.metrics.faithfulness is None
    assert result.metrics.answer_similarity is None
