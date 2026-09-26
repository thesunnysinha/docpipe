"""Optional speech and evaluation-provider settings."""

from typing import Literal

from pydantic import Field

from docpipe.config.settings_sections.base import Settings


class IntegrationSettings(Settings):
    """Configuration for optional speech transcription and Phoenix tracing."""

    # Speech-to-text (POST /transcribe)
    transcribe_default_backend: Literal["openai", "vibevoice", "vibevoice_remote"] = Field(
        default="openai", description="Speech transcription backend used when a request omits one."
    )
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for hosted transcription; treat as secret."
    )
    vibevoice_model_path: str = Field(
        default="microsoft/VibeVoice-ASR",
        description="Local VibeVoice model identifier or filesystem path.",
    )
    vibevoice_device: str = Field(
        default="auto", description="Compute device used by local VibeVoice inference."
    )
    vibevoice_attn_implementation: str = Field(
        default="auto",
        description="Attention implementation requested for local VibeVoice inference.",
    )
    vibevoice_max_new_tokens: int = Field(
        default=8192, description="Maximum generated tokens for VibeVoice transcription."
    )
    vibevoice_service_url: str | None = Field(
        default=None, description="Base URL for a remote Docpipe VibeVoice service."
    )
    vibevoice_remote_timeout: int = Field(
        default=600, description="Remote transcription request timeout in seconds."
    )

    phoenix_enabled: bool = Field(
        default=False, description="Enable optional Phoenix tracing for RAG and evaluation runs."
    )
    phoenix_collector_endpoint: str | None = Field(
        default=None, description="Phoenix collector endpoint used when Phoenix tracing is enabled."
    )
