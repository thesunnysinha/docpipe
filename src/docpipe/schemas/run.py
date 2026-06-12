"""POST /run schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from docpipe.core.types import ExtractionResult, ParsedDocument
from docpipe.schemas.base import ApiRequest, ApiResponse


class RunRequest(ApiRequest):
    """Parse a document and run structured extraction in one call."""

    source: str = Field(
        ...,
        min_length=1,
        description="File path or URL to parse.",
        examples=["/data/contract.pdf"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Natural-language extraction schema description.",
    )
    model_id: str = Field(
        ...,
        min_length=1,
        description="LLM model id for the extractor.",
        examples=["gpt-4o-mini"],
    )
    parser: str = Field(
        default="docling",
        description="Parser plugin name.",
        examples=["docling"],
    )
    extractor: str = Field(
        default="langextract",
        description="Extractor plugin name.",
        examples=["langextract"],
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Few-shot extraction examples for the schema.",
    )
    entity_classes: list[str] = Field(
        default_factory=list,
        description="Entity types to extract.",
        examples=[["party", "date", "amount"]],
    )


class RunResponse(ApiResponse):
    """Combined parse + extract pipeline output."""

    source: str = Field(..., description="Input source path or URL.")
    parsed: ParsedDocument = Field(..., description="Parsed document IR.")
    extractions: list[ExtractionResult] = Field(
        default_factory=list,
        description="Structured entities extracted from the document.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline-level metadata.",
    )
