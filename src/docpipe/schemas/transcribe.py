"""POST /transcribe schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from docpipe.schemas.base import ApiResponse


class TranscribeResponse(ApiResponse):
    """Speech-to-text transcription result."""

    text: str = Field(..., description="Full transcript text.")
    backend: str = Field(..., description="Transcription backend that produced the result.")
    raw_text: str | None = Field(
        default=None,
        description="Unnormalized transcript when the backend provides one.",
    )
    segments: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Time-aligned segments (shape varies by backend).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific metadata.",
    )
