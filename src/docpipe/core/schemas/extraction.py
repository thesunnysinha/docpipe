"""Structured extraction request and result schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    """Character-level grounding back to source text."""

    start: int = Field(...)
    end: int = Field(...)


class ExtractionResult(BaseModel):
    """Standardized extraction output from any extractor."""

    entity_class: str = Field(...)
    text: str = Field(...)
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_span: SourceSpan | None = Field(default=None)
    confidence: float | None = Field(default=None)


class ExtractionSchema(BaseModel):
    """Defines what to extract from text."""

    description: str = Field(...)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    entity_classes: list[str] = Field(default_factory=list)
    model_id: str = Field(...)
    output_model: Any = Field(
        default=None,
        description="Pydantic model class for LangChain structured output",
        exclude=True,
    )
    strict: bool = Field(default=True)
    extra: dict[str, Any] = Field(default_factory=dict)
