"""Route transcription requests to configured backends."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from docpipe.core.errors import ConfigurationError, TranscriptionError
from docpipe.speech.backends import openai_whisper, vibevoice_local, vibevoice_remote
from docpipe.speech.types import TranscribeBackend, TranscribeOutputFormat, TranscribeResult

if TYPE_CHECKING:
    from docpipe.config.settings import DocpipeSettings


class TranscriptionService:
    """Sync transcription facade; use ``atranscribe_file`` from async handlers."""

    @staticmethod
    def transcribe_file(
        audio_path: str,
        *,
        settings: DocpipeSettings,
        backend: TranscribeBackend | None = None,
        api_key: str | None = None,
        hotwords: list[str] | None = None,
        language: str | None = None,
        output_format: TranscribeOutputFormat = "plain",
    ) -> TranscribeResult:
        resolved = backend or settings.transcribe_default_backend  # type: ignore[assignment]
        if resolved not in ("openai", "vibevoice", "vibevoice_remote"):
            raise ConfigurationError(f"Unsupported transcription backend: {resolved}")

        if resolved == "openai":
            result = openai_whisper.transcribe_file(
                audio_path,
                api_key=api_key or settings.openai_api_key,
                language=language,
            )
        elif resolved == "vibevoice":
            result = vibevoice_local.transcribe_file(
                audio_path,
                model_path=settings.vibevoice_model_path,
                device=settings.vibevoice_device,
                attn_implementation=settings.vibevoice_attn_implementation,
                hotwords=hotwords,
                max_new_tokens=settings.vibevoice_max_new_tokens,
            )
        else:
            result = vibevoice_remote.transcribe_file(
                audio_path,
                service_url=settings.vibevoice_service_url,
                username=settings.username,
                password=settings.password,
                hotwords=hotwords,
                output_format=output_format,
                timeout=float(settings.vibevoice_remote_timeout),
            )

        if output_format == "plain" and not result.text and result.raw_text:
            result = result.model_copy(update={"text": result.raw_text.strip()})
        if output_format == "plain":
            return result.model_copy(update={"segments": []})
        return result

    @staticmethod
    async def atranscribe_file(
        audio_path: str,
        **kwargs: object,
    ) -> TranscribeResult:
        try:
            return await asyncio.to_thread(
                TranscriptionService.transcribe_file,
                audio_path,
                **kwargs,  # type: ignore[arg-type]
            )
        except (ConfigurationError, TranscriptionError):
            raise
        except Exception as exc:
            raise TranscriptionError(f"Transcription failed: {exc}") from exc
