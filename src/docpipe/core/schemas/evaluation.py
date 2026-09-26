"""Public RAG evaluation schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from docpipe.core.schemas.rag import RAGConfig


class EvalQuestion(BaseModel):
    """One evaluation prompt with expected answer and optional source ground truth."""

    question: str = Field(..., description="Question submitted to the RAG pipeline.")
    expected_answer: str = Field(..., description="Reference answer used to score the response.")
    expected_sources: list[str] = Field(
        default_factory=list,
        description="Optional source identifiers expected in retrieved context.",
    )


class EvalConfig(BaseModel):
    """Inputs and metric selection for a batch RAG evaluation run."""

    rag_config: RAGConfig = Field(..., description="RAG configuration applied to every question.")
    questions: list[EvalQuestion] = Field(
        ..., description="Ground-truth questions evaluated in this run."
    )
    evaluator: str = Field(default="builtin", description="Registered evaluator plugin name.")
    metrics: list[str] = Field(
        default_factory=lambda: ["hit_rate", "answer_similarity"],
        description="Metric identifiers requested from the evaluator.",
    )


class EvalMetrics(BaseModel):
    """Aggregate and per-question metrics returned by an evaluator.

    Metric values remain optional because evaluator implementations support
    different metric sets and may not produce a score for every requested metric.
    """

    hit_rate: float | None = Field(
        default=None,
        description="Evaluator-reported rate of expected sources found in retrieved results.",
    )
    mrr: float | None = Field(
        default=None, description="Mean reciprocal rank of the first expected source."
    )
    faithfulness: float | None = Field(
        default=None, description="Evaluator-reported grounding score for generated answers."
    )
    answer_similarity: float | None = Field(
        default=None,
        description="Evaluator-reported similarity between generated and reference answers.",
    )
    context_precision: float | None = Field(
        default=None, description="Evaluator-reported precision of retrieved context."
    )
    context_recall: float | None = Field(
        default=None, description="Evaluator-reported recall of retrieved context."
    )
    answer_relevancy: float | None = Field(
        default=None, description="Evaluator-reported relevance of answers to their questions."
    )
    per_question: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Metric details emitted for each evaluated question; shape depends on evaluator."
        ),
    )


class EvalResult(BaseModel):
    """Output of an EvalPipeline.run() call."""

    metrics: EvalMetrics = Field(..., description="Aggregate and per-question evaluation scores.")
    num_questions: int = Field(..., description="Number of questions processed by the evaluator.")
    timing_seconds: float = Field(
        ..., description="Elapsed wall-clock time for the evaluation run."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Evaluator-specific diagnostics and result metadata."
    )
