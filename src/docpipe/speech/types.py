"""Shared types for speech transcription."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TranscribeBackend = Literal["openai", "vibevoice", "vibevoice_remote"]
TranscribeOutputFormat = Literal["plain", "structured"]


class TranscriptionSegment(BaseModel):
    """One speaker-attributed segment returned by structured transcription."""

    start_time: str | float | None = Field(
        default=None, description="Segment start time in seconds or the backend's timestamp form."
    )
    end_time: str | float | None = Field(
        default=None, description="Segment end time in seconds or the backend's timestamp form."
    )
    speaker_id: str | int | None = Field(
        default=None, description="Optional speaker identifier assigned by the backend."
    )
    text: str = Field(default="", description="Recognized text for this segment.")


class TranscribeResult(BaseModel):
    """Normalized transcription output shared by all speech backends."""

    text: str = Field(..., description="Normalized recognized transcript text.")
    backend: str = Field(..., description="Backend identifier that produced this result.")
    raw_text: str | None = Field(
        default=None, description="Optional backend-native text before normalization."
    )
    segments: list[TranscriptionSegment] = Field(
        default_factory=list,
        description="Speaker-attributed segments when structured output is available.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Backend-specific timing or diagnostics metadata."
    )
