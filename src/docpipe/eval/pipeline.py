"""EvalPipeline: measure RAG quality with standard metrics."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from docpipe.core.errors import EvalError
from docpipe.core.types import EvalConfig, EvalMetrics, EvalQuestion, EvalResult, RAGResult
from docpipe.rag.pipeline import RAGPipeline

FAITHFULNESS_PROMPT = """\
You are evaluating whether an AI answer is faithful to the provided context.
Score 1 if the answer only contains information present in the context.
Score 0 if the answer contains information NOT present in the context.
Reply with only the number 0 or 1.

Context:
{context}

Answer:
{answer}

Score:"""

SIMILARITY_PROMPT = """\
You are evaluating the semantic similarity between an expected answer and an actual answer.
Score from 0.0 to 1.0, where 1.0 means identical meaning and 0.0 means completely different.
Reply with only a decimal number between 0.0 and 1.0.

Expected answer: {expected}
Actual answer: {actual}

Score:"""


class EvalPipeline:
    """Evaluate RAG quality using hit rate, MRR, faithfulness, and answer similarity."""

    def __init__(self, config: EvalConfig) -> None:
        self._config = config
        self._rag = RAGPipeline(config.rag_config)

    def run(self) -> EvalResult:
        """Run evaluation over all questions and compute aggregate metrics."""
        start = time.perf_counter()
        per_question: list[dict[str, Any]] = []

        for q in self._config.questions:
            row = self._evaluate_question(q)
            per_question.append(row)

        metrics = self._aggregate(per_question)
        return EvalResult(
            metrics=metrics,
            num_questions=len(self._config.questions),
            timing_seconds=time.perf_counter() - start,
        )

    async def arun(self) -> EvalResult:
        """Async variant."""
        return await asyncio.to_thread(self.run)

    # ── Per-question evaluation ───────────────────────────────────────────────

    def _evaluate_question(self, q: EvalQuestion) -> dict[str, Any]:
        try:
            result: RAGResult = self._rag.query(q.question)
        except Exception as e:
            raise EvalError(f"RAG query failed for '{q.question}': {e}") from e

        row: dict[str, Any] = {
            "question": q.question,
            "answer": result.answer,
            "expected_answer": q.expected_answer,
            "sources": result.sources,
            "expected_sources": q.expected_sources,
        }

        metrics = self._config.metrics

        if "hit_rate" in metrics and q.expected_sources:
            row["hit_rate"] = self._compute_hit_rate(q.expected_sources, result.sources)

        if "mrr" in metrics and q.expected_sources:
            row["mrr"] = self._compute_mrr(q.expected_sources, result.sources)

        if "faithfulness" in metrics:
            context = "\n\n".join(c.content for c in result.chunks)
            row["faithfulness"] = self._llm_judge_faithfulness(result.answer, context)

        if "answer_similarity" in metrics:
            row["answer_similarity"] = self._llm_judge_similarity(
                q.expected_answer, result.answer
            )

        return row

    # ── Metric implementations ────────────────────────────────────────────────

    @staticmethod
    def _compute_hit_rate(expected_sources: list[str], retrieved_sources: list[str]) -> float:
        for expected in expected_sources:
            for retrieved in retrieved_sources:
                if expected in retrieved or retrieved in expected:
                    return 1.0
        return 0.0

    @staticmethod
    def _compute_mrr(expected_sources: list[str], retrieved_sources: list[str]) -> float:
        for rank, retrieved in enumerate(retrieved_sources, 1):
            for expected in expected_sources:
                if expected in retrieved or retrieved in expected:
                    return 1.0 / rank
        return 0.0

    def _llm_judge_faithfulness(self, answer: str, context: str) -> float:
        from langchain_core.messages import HumanMessage

        prompt = FAITHFULNESS_PROMPT.format(context=context[:3000], answer=answer)
        try:
            response = self._rag._llm.invoke([HumanMessage(content=prompt)])
            score = float(response.content.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, AttributeError):
            return 0.0

    def _llm_judge_similarity(self, expected: str, actual: str) -> float:
        from langchain_core.messages import HumanMessage

        prompt = SIMILARITY_PROMPT.format(expected=expected, actual=actual)
        try:
            response = self._rag._llm.invoke([HumanMessage(content=prompt)])
            score = float(response.content.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, AttributeError):
            return 0.0

    # ── Aggregation ───────────────────────────────────────────────────────────

    def _aggregate(self, per_question: list[dict[str, Any]]) -> EvalMetrics:
        def mean(key: str) -> float | None:
            vals = [row[key] for row in per_question if key in row]
            return sum(vals) / len(vals) if vals else None

        return EvalMetrics(
            hit_rate=mean("hit_rate"),
            mrr=mean("mrr"),
            faithfulness=mean("faithfulness"),
            answer_similarity=mean("answer_similarity"),
            per_question=per_question,
        )
