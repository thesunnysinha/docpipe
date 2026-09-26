"""Result schema for parse-and-extract pipelines."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from docpipe.core.schemas.documents import ParsedDocument
from docpipe.core.schemas.extraction import ExtractionResult


class PipelineResult(BaseModel):
    """Combined output of document parsing and structured extraction."""

    source: str = Field(..., description="Original source path, URL, or source identifier.")
    parsed: ParsedDocument = Field(..., description="Parser-neutral document representation.")
    extractions: list[ExtractionResult] = Field(
        default_factory=list, description="Structured entities returned by the extractor."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline-level diagnostics and processing metadata.",
    )
