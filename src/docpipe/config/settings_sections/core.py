"""Core parser, plugin, vector-store, server, and observability defaults."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.config.settings_sections.base import Settings


class CoreSettings(Settings):
    """Settings shared by the primary ingestion and application runtime."""

    # Install profile (set in Docker OCI label / DOCPIPE_PROFILE)
    profile: Literal["slim", "balanced", "quality", "agents", "mcp", "eval", "gpu", "custom"] = (
        Field(
            default="balanced",
            description="Dependency and runtime profile used to select Docpipe defaults.",
        )
    )

    # Parser settings
    default_parser: str = Field(
        default="auto", description="Parser plugin used when a request omits one."
    )
    default_parser_tier: Literal["fast", "balanced", "quality"] = Field(
        default="balanced", description="Default quality tier for parser selection."
    )
    parser_options: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific options passed to the selected parser."
    )

    # Extractor settings
    default_extractor: str = Field(
        default="langextract", description="Extractor plugin used by default."
    )
    extractor_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific options passed to the selected extractor.",
    )

    # Ingestion / RAG defaults (used when request omits fields)
    default_chunker: str = Field(
        default="recursive", description="Chunker plugin used when ingestion omits one."
    )
    default_reranker: str = Field(
        default="none", description="Reranker plugin used when a RAG request omits one."
    )
    default_rag_strategy: str = Field(
        default="naive", description="Retrieval strategy used when a RAG request omits one."
    )
    default_evaluator: str = Field(
        default="builtin", description="Evaluator plugin used when evaluation omits one."
    )
    default_agent_backend: Literal["autogen", "langgraph", "runtime"] = Field(
        default="autogen", description="Agent framework selected when a request omits a backend."
    )
    default_runtime_preset: Literal["fast", "balanced", "quality", "agents"] = Field(
        default="balanced", description="Runtime preset used when a request omits a preset."
    )

    # Comma-separated allowlists; unset = all installed plugins allowed
    enabled_parsers: str | None = Field(
        default=None,
        description="Comma-separated parser allowlist; unset permits installed parsers.",
    )
    enabled_extractors: str | None = Field(
        default=None,
        description="Comma-separated extractor allowlist; unset permits installed extractors.",
    )
    enabled_chunkers: str | None = Field(
        default=None,
        description="Comma-separated chunker allowlist; unset permits installed chunkers.",
    )
    enabled_rerankers: str | None = Field(
        default=None,
        description="Comma-separated reranker allowlist; unset permits installed rerankers.",
    )
    enabled_evaluators: str | None = Field(
        default=None,
        description="Comma-separated evaluator allowlist; unset permits installed evaluators.",
    )
    enabled_sources: str | None = Field(
        default=None,
        description="Comma-separated source allowlist; unset permits installed sources.",
    )
    enabled_vectorstores: str | None = Field(
        default=None,
        description="Comma-separated vector-store allowlist; unset permits installed stores.",
    )
    disabled_plugins: str | None = Field(
        default=None,
        description="Comma-separated plugin names denied regardless of category allowlists.",
    )
    # Temporary vector-ingestion rollback; source resolution remains policy-gated.
    plugin_foundation_enabled: bool = Field(
        default=True, description="Enable the plugin-based vector ingestion compatibility path."
    )

    # Ingestion settings
    db_connection_string: str | None = Field(
        default=None, description="Default vector database connection URL; keep credentials secret."
    )
    db_table_name: str = Field(
        default="docpipe_documents",
        description="Default collection or table for stored document chunks.",
    )
    # Vector store: pgvector (default) or optional local turbovec file indices
    vector_backend: Literal["pgvector", "turbovec"] = Field(
        default="pgvector",
        description="Default vector-store implementation for legacy-compatible configuration.",
    )
    vector_store: VectorStoreOptions | None = Field(
        default=None, description="Provider-neutral vector-store selection and options."
    )
    turbovec_index_dir: Path = Field(
        default=Path(".docpipe/indices"),
        description="Directory used for local TurboVec index files.",
    )
    turbovec_bit_width: int = Field(
        default=4, description="Quantization bit width used by TurboVec indexes."
    )
    embedding_provider: str | None = Field(
        default=None, description="Default embedding provider registry name."
    )
    embedding_model: str | None = Field(
        default=None, description="Default embedding model identifier."
    )
    chunk_size: int = Field(default=1000, description="Default maximum chunk size in characters.")
    chunk_overlap: int = Field(
        default=200, description="Default overlap in characters between adjacent chunks."
    )
    ingest_mode: str = Field(
        default="both", description="Default ingestion output mode: chunks, extractions, or both."
    )

    # Server and pipeline settings
    server_host: str = Field(
        default="0.0.0.0", description="Address on which the HTTP server listens."
    )
    server_port: int = Field(default=8000, description="TCP port on which the HTTP server listens.")
    max_concurrency: int = Field(
        default=4, description="Maximum number of concurrent blocking pipeline operations."
    )

    # Logging
    log_level: str = Field(
        default="INFO", description="Minimum severity emitted by Docpipe loggers."
    )
    log_format: str = Field(
        default="text", description="Log output format, such as text or structured JSON."
    )
    http_request_logging_enabled: bool = Field(
        default=True, description="Log HTTP request method, path, status, and duration."
    )

    # OpenTelemetry (optional — install docpipe-sdk[observability])
    otel_enabled: bool = Field(
        default=False, description="Enable OpenTelemetry tracing and metrics instrumentation."
    )
    otel_service_name: str = Field(
        default="docpipe", description="Service name attached to OpenTelemetry resources."
    )
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, description="OTLP collector endpoint; unset uses exporter defaults."
    )
    otel_exporter_otlp_headers: str | None = Field(
        default=None, description="OTLP exporter authorization headers; treat as secret."
    )
    otel_traces_sampler: str = Field(
        default="parentbased_traceidratio",
        description="OpenTelemetry trace sampler implementation name.",
    )
    otel_traces_sampler_arg: float = Field(
        default=1.0, description="Sampler argument, typically the trace sampling ratio from 0 to 1."
    )
    otel_semconv_stability_opt_in: str = Field(
        default="gen_ai_latest_experimental",
        description="Semantic-convention stability groups enabled for telemetry.",
    )

    # Health probes and model artifacts
    health_check_db: bool = Field(
        default=True, description="Check configured database connectivity in health probes."
    )
    health_check_embedding: bool = Field(
        default=False, description="Check embedding-provider connectivity in health probes."
    )
    model_cache_dir: Path | None = Field(
        default=None,
        description="Directory for locally cached model artifacts; unset uses library defaults.",
    )
    parser_cache_ttl_seconds: int = Field(
        default=0, description="Parser-result cache lifetime in seconds; zero disables caching."
    )
