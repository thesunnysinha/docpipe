"""RAGAS evaluator unit tests with mocked ragas.evaluate."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from docpipe.core.types import EvalConfig, EvalQuestion, RAGConfig
from docpipe.eval.ragas_evaluator import RagasEvaluator


def _eval_config() -> EvalConfig:
    return EvalConfig(
        rag_config=RAGConfig(
            connection_string="postgresql://test/db",
            table_name="docs",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            strategy="naive",
        ),
        questions=[EvalQuestion(question="What?", expected_answer="42")],
        evaluator="ragas",
        metrics=["faithfulness"],
    )


def _fake_ragas_modules(scores: MagicMock) -> dict[str, ModuleType]:
    datasets = ModuleType("datasets")
    datasets.Dataset = MagicMock(from_list=MagicMock(return_value=MagicMock()))

    metrics = ModuleType("ragas.metrics")
    metrics.faithfulness = MagicMock()
    metrics.answer_relevancy = MagicMock()
    metrics.context_precision = MagicMock()
    metrics.context_recall = MagicMock()

    ragas = ModuleType("ragas")
    ragas.evaluate = MagicMock(return_value=scores)

    return {
        "datasets": datasets,
        "ragas": ragas,
        "ragas.metrics": metrics,
    }


@patch.object(RagasEvaluator, "is_available", return_value=True)
@patch("docpipe.eval.ragas_evaluator.RAGPipeline")
def test_ragas_evaluator_returns_metrics(
    mock_pipeline_cls: MagicMock,
    _available: MagicMock,
) -> None:
    rag = MagicMock()
    chunk = MagicMock(content="context")
    rag.query.return_value = MagicMock(answer="forty-two", chunks=[chunk])
    mock_pipeline_cls.return_value = rag

    mean_row = MagicMock()
    mean_row.to_dict.return_value = {"faithfulness": 0.9}
    scores = MagicMock()
    scores.to_pandas.return_value.mean.return_value = mean_row

    modules = _fake_ragas_modules(scores)
    with patch.dict(sys.modules, modules):
        result = RagasEvaluator().evaluate(_eval_config())

    assert result.num_questions == 1
    assert result.metrics.faithfulness == 0.9
