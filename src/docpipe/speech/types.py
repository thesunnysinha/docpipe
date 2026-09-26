"""Shared types for speech transcription."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TranscribeBackend = Literal["openai", "vibevoice", "vibevoice_remote"]
TranscribeOutputFormat = Literal["plain", "structured"]


class TranscriptionSegment(BaseModel):
    start_time: str | float | None = Field(default=None)
    end_time: str | float | None = Field(default=None)
    speaker_id: str | int | None = Field(default=None)
    text: str = Field(default="")


class TranscribeResult(BaseModel):
    text: str = Field(...)
    backend: str = Field(...)
    raw_text: str | None = Field(default=None)
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
