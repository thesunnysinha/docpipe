"""POST /extract schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from docpipe.core.types import ExtractionResult
from docpipe.schemas.base import ApiRequest, ApiResponse


class ExtractRequest(ApiRequest):
    """Run structured extraction on pre-parsed text."""

    text: str = Field(..., min_length=1, description="Document text to extract from.")
    description: str = Field(
        ...,
        min_length=1,
        description="Natural-language schema description.",
    )
    model_id: str = Field(..., min_length=1, description="LLM model id for extraction.")
    extractor: str = Field(
        default="langextract",
        description="Extractor plugin name.",
        examples=["langextract"],
    )
    strict: bool = Field(
        default=True,
        description="When true, reject outputs that violate the schema.",
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Few-shot examples for the extraction schema.",
    )
    entity_classes: list[str] = Field(
        default_factory=list,
        description="Entity types to extract.",
    )


class ExtractResponse(ApiResponse):
    """Structured extraction results."""

    extractions: list[ExtractionResult] = Field(
        default_factory=list,
        description="Extracted entities with optional grounding spans.",
    )
