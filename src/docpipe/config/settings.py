"""Pydantic Settings for docpipe configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class DocpipeSettings(BaseSettings):
    """Configuration loaded from env vars, YAML, or constructor."""

    model_config = {"env_prefix": "DOCPIPE_", "env_nested_delimiter": "__"}

    # Parser settings
    default_parser: str = "docling"
    parser_options: dict[str, Any] = Field(default_factory=dict)

    # Extractor settings
    default_extractor: str = "langextract"
    extractor_options: dict[str, Any] = Field(default_factory=dict)

    # Ingestion settings
    db_connection_string: str | None = None
    db_table_name: str = "docpipe_documents"
    # Vector store: pgvector (default) or optional local turbovec file indices
    vector_backend: Literal["pgvector", "turbovec"] = "pgvector"
    turbovec_index_dir: Path = Field(default=Path(".docpipe/indices"))
    turbovec_bit_width: int = 4
    embedding_provider: str | None = None
    embedding_model: str | None = None
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_mode: str = "both"

    # Server settings
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Pipeline settings
    max_concurrency: int = 4

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"
    http_request_logging_enabled: bool = True

    # OpenTelemetry (optional — install docpipe-sdk[observability])
    otel_enabled: bool = False
    otel_service_name: str = "docpipe"
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None
    otel_traces_sampler: str = "parentbased_traceidratio"
    otel_traces_sampler_arg: float = 1.0
    otel_semconv_stability_opt_in: str = "gen_ai_latest_experimental"

    # Health probes
    health_check_db: bool = True
    health_check_embedding: bool = False

    # Security
    # Set DOCPIPE_ALLOW_PRIVATE_URLS=true in environments where document sources
    # may resolve to private/internal network addresses (e.g. Docker Compose where
    # MinIO or other storage runs on the same network). Disabled by default to
    # prevent SSRF in public deployments.
    allow_private_urls: bool = False

    # Speech-to-text (POST /transcribe)
    # openai: Whisper via OPENAI_API_KEY | vibevoice: local GPU (pip install VibeVoice)
    # vibevoice_remote: proxy to another docpipe with VibeVoice loaded
    transcribe_default_backend: Literal["openai", "vibevoice", "vibevoice_remote"] = "openai"
    openai_api_key: str | None = None
    vibevoice_model_path: str = "microsoft/VibeVoice-ASR"
    vibevoice_device: str = "auto"
    vibevoice_attn_implementation: str = "auto"
    vibevoice_max_new_tokens: int = 8192
    vibevoice_service_url: str | None = None
    vibevoice_remote_timeout: int = 600

    # Authentication
    # HTTP Basic Auth protecting all API endpoints and the web UI.
    # Disable entirely with DOCPIPE_AUTH_ENABLED=false for trusted internal networks.
    # Change defaults with DOCPIPE_USERNAME / DOCPIPE_PASSWORD before deploying.
    auth_enabled: bool = True
    username: str = "admin"
    password: str = "docpipe"
