"""POST /transcribe schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    text: str
    backend: str
    raw_text: str | None = None
    segments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
