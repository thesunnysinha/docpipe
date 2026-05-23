"""POST /evaluate/run schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from docpipe.schemas.common import TableNameFieldMixin


class EvaluateRequest(TableNameFieldMixin):
    questions: list[dict[str, Any]]
    connection_string: str
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    llm_model: str
    strategy: str = "naive"
    metrics: list[str] = Field(default_factory=lambda: ["hit_rate", "answer_similarity"])


class EvaluateResponse(BaseModel):
    metrics: dict[str, Any]
    num_questions: int
    timing_seconds: float
