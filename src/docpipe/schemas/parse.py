"""POST /parse schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from docpipe.schemas.base import ApiRequest, ApiResponse


class ParseRequest(ApiRequest):
    """Parse a document into text or markdown."""

    source: str = Field(
        ...,
        min_length=1,
        description="File path or URL to parse.",
        examples=["/data/report.pdf"],
    )
    parser: str | None = Field(
        default=None,
        description="Parser plugin name; resolved from preset when omitted.",
    )
    tier: str | None = Field(
        default=None,
        description="Parser quality tier: fast, balanced, or quality.",
    )
    preset: str | None = Field(
        default=None,
        description="Runtime preset: fast, balanced, quality, or agents.",
        examples=["balanced"],
    )
    output_format: Literal["markdown", "text", "json"] = Field(
        default="markdown",
        description="Serialized output format.",
    )


class ParseResponse(ApiResponse):
    """Parsed document content."""

    source: str = Field(..., description="Input source path or URL.")
    format: str = Field(..., description="Detected document format.")
    content: str = Field(..., description="Serialized document content.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Parser-specific metadata.",
    )
