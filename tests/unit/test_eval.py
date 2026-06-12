"""Unit tests for EvalPipeline — all external calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.types import EvalConfig, EvalQuestion, RAGChunk, RAGConfig, RAGResult
from docpipe.eval.builtin_evaluator import BuiltinEvaluator
from docpipe.eval.pipeline import EvalPipeline
from docpipe.registry.registry import PluginRegistry


def _make_rag_config() -> RAGConfig:
    return RAGConfig(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o",
        system_prompt="ctx={context} q={question}",
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


@pytest.fixture(autouse=True)
def _register_builtin_evaluator():
    PluginRegistry.get().register_evaluator("builtin", BuiltinEvaluator)


def test_eval_config_defaults() -> None:
    cfg = EvalConfig(rag_config=_make_rag_config(), questions=[])
    assert cfg.metrics == ["hit_rate", "answer_similarity"]
    assert cfg.evaluator == "builtin"


@patch("docpipe.eval.builtin_evaluator.RAGPipeline")
def test_hit_rate_when_source_retrieved(mock_rag_cls: MagicMock) -> None:
    mock_rag = MagicMock()
    mock_rag.query.return_value = _fake_rag_result(sources=["report.pdf"])
    mock_rag._llm = MagicMock()
    mock_rag_cls.return_value = mock_rag

    cfg = _make_eval_config(metrics=["hit_rate"])
    result = EvalPipeline(cfg).run()

    assert result.metrics.hit_rate == pytest.approx(1.0)


@patch("docpipe.eval.builtin_evaluator.RAGPipeline")
def test_hit_rate_when_source_not_retrieved(mock_rag_cls: MagicMock) -> None:
    mock_rag = MagicMock()
    mock_rag.query.return_value = _fake_rag_result(sources=["other.pdf"])
    mock_rag._llm = MagicMock()
    mock_rag_cls.return_value = mock_rag

    cfg = _make_eval_config(metrics=["hit_rate"])
    result = EvalPipeline(cfg).run()

    assert result.metrics.hit_rate == pytest.approx(0.0)


@patch("docpipe.eval.builtin_evaluator.RAGPipeline")
def test_mrr_first_position(mock_rag_cls: MagicMock) -> None:
    mock_rag = MagicMock()
    mock_rag.query.return_value = _fake_rag_result(sources=["report.pdf", "other.pdf"])
    mock_rag._llm = MagicMock()
    mock_rag_cls.return_value = mock_rag

    cfg = _make_eval_config(metrics=["mrr"])
    result = EvalPipeline(cfg).run()

    assert result.metrics.mrr == pytest.approx(1.0)


@patch("docpipe.eval.builtin_evaluator.RAGPipeline")
def test_answer_similarity_llm_judge(mock_rag_cls: MagicMock) -> None:
    mock_rag = MagicMock()
    mock_rag.query.return_value = _fake_rag_result()
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="0.85")
    mock_rag._llm = llm
    mock_rag_cls.return_value = mock_rag

    cfg = _make_eval_config(metrics=["answer_similarity"])
    result = EvalPipeline(cfg).run()

    assert result.metrics.answer_similarity == pytest.approx(0.85)


@patch("docpipe.eval.builtin_evaluator.RAGPipeline")
def test_eval_result_metadata(mock_rag_cls: MagicMock) -> None:
    mock_rag = MagicMock()
    mock_rag.query.return_value = _fake_rag_result(sources=["f.pdf"])
    mock_rag._llm = MagicMock()
    mock_rag_cls.return_value = mock_rag

    questions = [
        EvalQuestion(question="Q1?", expected_answer="A1", expected_sources=["f.pdf"]),
        EvalQuestion(question="Q2?", expected_answer="A2", expected_sources=["f.pdf"]),
    ]
    cfg = _make_eval_config(questions=questions, metrics=["hit_rate"])
    result = EvalPipeline(cfg).run()

    assert result.num_questions == 2
    assert result.timing_seconds > 0
    assert len(result.metrics.per_question) == 2


@patch("docpipe.eval.builtin_evaluator.RAGPipeline")
def test_unselected_metrics_are_none(mock_rag_cls: MagicMock) -> None:
    mock_rag = MagicMock()
    mock_rag.query.return_value = _fake_rag_result()
    mock_rag._llm = MagicMock()
    mock_rag_cls.return_value = mock_rag

    cfg = _make_eval_config(metrics=["hit_rate"])
    result = EvalPipeline(cfg).run()

    assert result.metrics.mrr is None
    assert result.metrics.faithfulness is None
    assert result.metrics.answer_similarity is None
