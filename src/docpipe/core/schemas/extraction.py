"""Structured extraction request and result schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    """Half-open character offsets grounding an extracted value in source text."""

    start: int = Field(
        ..., description="Zero-based character offset where the span begins, inclusive."
    )
    end: int = Field(..., description="Zero-based character offset where the span ends, exclusive.")


class ExtractionResult(BaseModel):
    """Standardized extraction output from any extractor."""

    entity_class: str = Field(..., description="Entity type assigned by the extraction schema.")
    text: str = Field(..., description="Extracted entity text as represented in the source.")
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Additional structured properties emitted for the entity."
    )
    source_span: SourceSpan | None = Field(
        default=None,
        description="Optional character offsets locating the entity in the input text.",
    )
    confidence: float | None = Field(
        default=None,
        description=(
            "Optional confidence score emitted by the extractor; scale is backend-dependent."
        ),
    )


class ExtractionSchema(BaseModel):
    """Defines the requested entity types and output contract for extraction."""

    description: str = Field(
        ..., description="Natural-language instructions describing the desired extraction."
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Optional few-shot input/output examples for the extractor.",
    )
    entity_classes: list[str] = Field(
        default_factory=list, description="Optional allowed or expected entity type names."
    )
    model_id: str = Field(
        ..., description="Model identifier passed to the selected extraction backend."
    )
    output_model: Any = Field(
        default=None,
        description="Pydantic model class for LangChain structured output",
        exclude=True,
    )
    strict: bool = Field(
        default=True,
        description="Whether the backend should enforce the requested structured-output contract.",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific extraction options not represented by common fields.",
    )
