"""Proxy transcription to another docpipe (or compatible) HTTP service."""

from __future__ import annotations

import os
from typing import Any

from docpipe.core.errors import ConfigurationError, TranscriptionError
from docpipe.speech.types import TranscribeResult, TranscriptionSegment

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


def transcribe_file(
    audio_path: str,
    *,
    service_url: str | None,
    username: str,
    password: str,
    hotwords: list[str] | None = None,
    output_format: str = "plain",
    timeout: float = 600.0,
) -> TranscribeResult:
    if httpx is None:
        raise ConfigurationError(
            "Remote VibeVoice backend requires httpx. Install with: pip install 'docpipe-sdk[http]'"
        )
    base = (service_url or os.environ.get("DOCPIPE_VIBEVOICE_SERVICE_URL") or "").rstrip("/")
    if not base:
        raise ConfigurationError(
            "vibevoice_remote backend requires DOCPIPE_VIBEVOICE_SERVICE_URL or "
            "vibevoice_service_url in settings."
        )

    filename = os.path.basename(audio_path)
    data: dict[str, str] = {
        "backend": "vibevoice",
        "output_format": output_format,
    }
    if hotwords:
        data["hotwords"] = ",".join(hotwords)

    try:
        with open(audio_path, "rb") as audio_file, httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base}/transcribe",
                auth=(username, password),
                files={"file": (filename, audio_file)},
                data=data,
            )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except Exception as exc:
        raise TranscriptionError(f"Remote VibeVoice service failed: {exc}") from exc

    segments = [
        TranscriptionSegment(**seg)
        for seg in (payload.get("segments") or [])
        if isinstance(seg, dict)
    ]
    return TranscribeResult(
        text=str(payload.get("text", "")).strip(),
        backend="vibevoice_remote",
        raw_text=payload.get("raw_text"),
        segments=segments,
        metadata={"service_url": base},
    )
