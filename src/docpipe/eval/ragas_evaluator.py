"""RAGAS-backed RAG evaluation."""

from __future__ import annotations

import time
from typing import Any

from docpipe.core.errors import ConfigurationError, EvalError
from docpipe.core.types import EvalConfig, EvalMetrics, EvalResult
from docpipe.rag.pipeline import RAGPipeline


class RagasEvaluator:
    """Evaluate RAG using the RAGAS metrics library."""

    name = "ragas"
    license = "Apache-2.0"
    requires_gpu = False

    def evaluate(self, config: EvalConfig) -> EvalResult:
        if not self.is_available():
            raise ConfigurationError(
                "RAGAS is not installed. Install with: pip install docpipe-sdk[eval-ragas]"
            )

        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        start = time.perf_counter()
        rag = RAGPipeline(config.rag_config)
        rows: list[dict[str, Any]] = []

        for q in config.questions:
            try:
                result = rag.query(q.question)
            except Exception as e:
                raise EvalError(f"RAG query failed for '{q.question}': {e}") from e
            rows.append(
                {
                    "question": q.question,
                    "answer": result.answer,
                    "contexts": [c.content for c in result.chunks],
                    "ground_truth": q.expected_answer,
                }
            )

        dataset = Dataset.from_list(rows)
        metric_map = {
            "faithfulness": faithfulness,
            "context_precision": context_precision,
            "context_recall": context_recall,
            "answer_relevancy": answer_relevancy,
        }
        selected = [metric_map[m] for m in config.metrics if m in metric_map]
        if not selected:
            selected = [faithfulness, answer_relevancy]

        try:
            scores = ragas_evaluate(dataset, metrics=selected)
        except Exception as e:
            raise EvalError(f"RAGAS evaluation failed: {e}") from e

        score_dict = scores.to_pandas().mean(numeric_only=True).to_dict()
        per_question = [
            {
                "question": row["question"],
                "answer": row["answer"],
                "expected_answer": row["ground_truth"],
            }
            for row in rows
        ]

        return EvalResult(
            metrics=EvalMetrics(
                faithfulness=_safe_float(score_dict.get("faithfulness")),
                context_precision=_safe_float(score_dict.get("context_precision")),
                context_recall=_safe_float(score_dict.get("context_recall")),
                answer_relevancy=_safe_float(score_dict.get("answer_relevancy")),
                per_question=per_question,
            ),
            num_questions=len(config.questions),
            timing_seconds=time.perf_counter() - start,
            metadata={"evaluator": self.name},
        )

    @classmethod
    def is_available(cls) -> bool:
        try:
            import ragas  # noqa: F401

            return True
        except ImportError:
            return False


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
