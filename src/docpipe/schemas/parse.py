"""POST /parse schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    source: str
    parser: str = "docling"
    output_format: str = "markdown"


class ParseResponse(BaseModel):
    source: str
    format: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
