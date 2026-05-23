"""OpenAI Whisper transcription backend."""

from __future__ import annotations

import os
from typing import Any

from docpipe.core.errors import ConfigurationError, TranscriptionError
from docpipe.speech.types import TranscribeResult


def transcribe_file(
    audio_path: str,
    *,
    api_key: str | None,
    language: str | None = None,
) -> TranscribeResult:
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ConfigurationError(
            "OpenAI transcription requires api_key in the request or OPENAI_API_KEY."
        )

    try:
        from openai import OpenAI
    except ImportError as err:
        raise ConfigurationError(
            "OpenAI backend requires openai. Install: pip install 'docpipe-sdk[openai]'"
        ) from err

    client = OpenAI(api_key=api_key)
    kwargs: dict[str, Any] = {"model": "whisper-1"}
    if language:
        kwargs["language"] = language

    try:
        with open(audio_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(file=audio_file, **kwargs)
    except Exception as exc:
        raise TranscriptionError(f"OpenAI Whisper transcription failed: {exc}") from exc

    text = getattr(result, "text", "") or ""
    return TranscribeResult(text=text.strip(), backend="openai", raw_text=text)
