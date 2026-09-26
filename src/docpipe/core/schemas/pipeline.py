"""Result schema for parse-and-extract pipelines."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from docpipe.core.schemas.documents import ParsedDocument
from docpipe.core.schemas.extraction import ExtractionResult


class PipelineResult(BaseModel):
    """Full pipeline output: parsed document plus extractions."""

    source: str = Field(...)
    parsed: ParsedDocument = Field(...)
    extractions: list[ExtractionResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
