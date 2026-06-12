"""POST /evaluate/run schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from docpipe.core.types import EvalQuestion
from docpipe.schemas.base import ApiResponse
from docpipe.schemas.common import TableNameFieldMixin


class EvaluateRequest(TableNameFieldMixin):
    """Batch RAG evaluation against ground-truth questions."""

    questions: list[EvalQuestion] = Field(
        ...,
        min_length=1,
        description="Ground-truth Q&A pairs with optional expected sources.",
    )
    connection_string: str = Field(..., min_length=1, description="Vector store connection string.")
    embedding_provider: str = Field(..., min_length=1, description="Embedding provider name.")
    embedding_model: str = Field(..., min_length=1, description="Embedding model id.")
    llm_provider: str = Field(..., min_length=1, description="LLM provider for answer generation.")
    llm_model: str = Field(..., min_length=1, description="LLM model id.")
    strategy: str | None = Field(
        default=None,
        description="RAG retrieval strategy override.",
    )
    preset: str | None = Field(
        default=None,
        description="Runtime preset: fast, balanced, quality, or agents.",
        examples=["balanced"],
    )
    evaluator: str | None = Field(
        default=None,
        description="Evaluator plugin name.",
    )
    metrics: list[str] = Field(
        default_factory=lambda: ["hit_rate", "answer_similarity"],
        description="Metric names to compute.",
    )


class EvaluateResponse(ApiResponse):
    """Aggregated evaluation metrics."""

    metrics: dict[str, Any] = Field(..., description="Per-metric scores and details.")
    num_questions: int = Field(..., ge=0, description="Number of questions evaluated.")
    timing_seconds: float = Field(..., ge=0, description="Wall-clock runtime in seconds.")
