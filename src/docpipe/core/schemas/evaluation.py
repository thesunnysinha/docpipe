"""Public RAG evaluation schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from docpipe.core.schemas.rag import RAGConfig


class EvalQuestion(BaseModel):
    """A single question with ground truth for RAG evaluation."""

    question: str = Field(...)
    expected_answer: str = Field(...)
    expected_sources: list[str] = Field(default_factory=list)


class EvalConfig(BaseModel):
    """Configuration for the evaluation pipeline."""

    rag_config: RAGConfig = Field(...)
    questions: list[EvalQuestion] = Field(...)
    evaluator: str = Field(default="builtin")
    metrics: list[str] = Field(default_factory=lambda: ["hit_rate", "answer_similarity"])


class EvalMetrics(BaseModel):
    """Aggregate evaluation metrics."""

    hit_rate: float | None = Field(default=None)
    mrr: float | None = Field(default=None)
    faithfulness: float | None = Field(default=None)
    answer_similarity: float | None = Field(default=None)
    context_precision: float | None = Field(default=None)
    context_recall: float | None = Field(default=None)
    answer_relevancy: float | None = Field(default=None)
    per_question: list[dict[str, Any]] = Field(default_factory=list)


class EvalResult(BaseModel):
    """Output of an EvalPipeline.run() call."""

    metrics: EvalMetrics = Field(...)
    num_questions: int = Field(...)
    timing_seconds: float = Field(...)
    metadata: dict[str, Any] = Field(default_factory=dict)
