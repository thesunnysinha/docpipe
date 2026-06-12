"""Speech transcription."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Literal

from fastapi import Request

from docpipe.config.settings import DocpipeSettings
from docpipe.schemas import TranscribeResponse
from docpipe.speech.service import TranscriptionService

logger = logging.getLogger(__name__)


class TranscribeService:
    def __init__(self, settings: DocpipeSettings) -> None:
        self._settings = settings

    async def transcribe(self, request: Request) -> TranscribeResponse:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise ValueError("Multipart field 'file' is required.")

        backend_raw = form.get("backend")
        backend: Literal["openai", "vibevoice", "vibevoice_remote"] | None = None
        if backend_raw in ("openai", "vibevoice", "vibevoice_remote"):
            backend = backend_raw  # type: ignore[assignment]

        output_raw = form.get("output_format") or "plain"
        output_format: Literal["plain", "structured"] = (
            "structured" if output_raw == "structured" else "plain"
        )
        hotwords_raw = form.get("hotwords")
        api_key_raw = form.get("api_key")
        language_raw = form.get("language")

        filename = getattr(upload, "filename", None) or "audio.wav"
        suffix = os.path.splitext(filename)[1] or ".wav"
        hotword_list = [w.strip() for w in str(hotwords_raw or "").split(",") if w.strip()]
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                temp_path = tmp.name
                while chunk := await upload.read(1024 * 1024):
                    tmp.write(chunk)
            result = await TranscriptionService.atranscribe_file(
                temp_path,
                settings=self._settings,
                backend=backend,
                api_key=str(api_key_raw) if api_key_raw else None,
                hotwords=hotword_list or None,
                language=str(language_raw) if language_raw else None,
                output_format=output_format,
            )
            return TranscribeResponse(
                text=result.text,
                backend=result.backend,
                raw_text=result.raw_text,
                segments=[seg.model_dump() for seg in result.segments],
                metadata=result.metadata,
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    logger.warning("Failed to remove temp audio file", exc_info=True)
