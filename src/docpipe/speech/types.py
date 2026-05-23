"""Shared types for speech transcription."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TranscribeBackend = Literal["openai", "vibevoice", "vibevoice_remote"]
TranscribeOutputFormat = Literal["plain", "structured"]


class TranscriptionSegment(BaseModel):
    start_time: str | float | None = None
    end_time: str | float | None = None
    speaker_id: str | int | None = None
    text: str = ""


class TranscribeResult(BaseModel):
    text: str
    backend: str
    raw_text: str | None = None
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
