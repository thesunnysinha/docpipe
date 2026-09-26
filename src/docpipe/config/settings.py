"""Pydantic Settings for docpipe configuration."""

from __future__ import annotations

import ipaddress
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, JsonValue, SecretStr, field_validator
from pydantic_settings import BaseSettings

from docpipe.config.plugin_options import VectorStoreOptions


class DocpipeSettings(BaseSettings):
    """Configuration loaded from env vars, YAML, or constructor."""

    model_config = {"env_prefix": "DOCPIPE_", "env_nested_delimiter": "__"}

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
    default_agent_backend: Literal["autogen", "langgraph"] = Field(
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

    # Server settings
    server_host: str = Field(
        default="0.0.0.0", description="Address on which the HTTP server listens."
    )
    server_port: int = Field(default=8000, description="TCP port on which the HTTP server listens.")

    # Pipeline settings
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

    # Health probes
    health_check_db: bool = Field(
        default=True, description="Check configured database connectivity in health probes."
    )
    health_check_embedding: bool = Field(
        default=False, description="Check embedding-provider connectivity in health probes."
    )

    # Model artifacts (CrossEncoder, GLM-OCR, HF caches)
    model_cache_dir: Path | None = Field(
        default=None,
        description="Directory for locally cached model artifacts; unset uses library defaults.",
    )

    # In-memory parse cache TTL; 0 disables caching
    parser_cache_ttl_seconds: int = Field(
        default=0, description="Parser-result cache lifetime in seconds; zero disables caching."
    )

    # Optional RAG response KV cache. Redis is operator-managed and may be shared
    # by replicas; process memory is bounded but never distributed or durable.
    rag_cache_enabled: bool = Field(
        default=False, description="Enable exact-question answer caching for HTTP RAG requests."
    )
    rag_cache_backend: Literal["memory", "redis"] = Field(
        default="memory", description="RAG cache backend; Redis requires the rag-redis extra."
    )
    rag_cache_redis_url: str | None = Field(
        default=None,
        description="Operator-managed Redis URL; keep credentials secret and prefer TLS/ACLs.",
    )
    rag_cache_ttl_seconds: int = Field(
        default=300, ge=1, le=86_400, description="Maximum lifetime of a cached RAG answer."
    )
    rag_cache_max_entries: int = Field(
        default=10_000,
        ge=1,
        le=1_000_000,
        description="Maximum entries for process-local RAG cache.",
    )
    rag_cache_max_payload_bytes: int = Field(
        default=256 * 1024,
        ge=1024,
        le=10 * 1024 * 1024,
        description="Maximum serialized answer size eligible for the RAG cache.",
    )
    rag_cache_socket_timeout_seconds: float = Field(
        default=1.0,
        gt=0,
        le=30,
        description="Redis connect/read timeout; cache outages fall back to uncached RAG.",
    )

    # Optional hosted MCP endpoint. Tokens are operator-provisioned bearer
    # credentials; host rules are mandatory to protect the HTTP transport.
    mcp_server_enabled: bool = Field(
        default=False, description="Expose the standard Streamable HTTP MCP endpoint at /mcp."
    )
    mcp_operator_tokens: tuple[SecretStr, ...] = Field(
        default_factory=tuple,
        description=(
            "Operator-managed bearer tokens for MCP clients; provide as a JSON list secret."
        ),
    )
    mcp_allowed_hosts: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Exact HTTP Host values trusted by the MCP transport; wildcards are rejected.",
    )
    mcp_allowed_origins: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Exact browser origins allowed by the MCP transport; wildcards are rejected.",
    )
    mcp_tool_timeout_seconds: float = Field(
        default=300.0,
        gt=0,
        le=3600,
        description="Maximum duration in seconds for one MCP tool call.",
    )
    mcp_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=10_000,
        description="Maximum MCP HTTP POST requests per minute per transport peer.",
    )
    mcp_tenant_id: str | None = Field(
        default=None,
        description=(
            "Operator-assigned tenant scope for MCP bearer clients when tenant policies "
            "are enabled."
        ),
    )

    # Source resolution. Provider-specific request envelopes are introduced by
    # the plugin configuration layer; these values remain safe process defaults.
    # Local-path ingestion is disabled until an operator grants explicit roots;
    # defaulting to CWD can expose mounted secrets and application files.
    source_allowed_roots: tuple[Path, ...] = Field(
        default_factory=tuple,
        description="Filesystem roots local-source plugins may read; empty denies local access.",
    )
    source_temporary_root: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "docpipe-sources",
        description="Private temporary directory used while downloading or resolving sources.",
    )
    source_max_bytes: int = Field(
        default=100 * 1024 * 1024, ge=1, description="Maximum source payload size in bytes."
    )
    source_chunk_bytes: int = Field(
        default=1024 * 1024,
        ge=1,
        le=8 * 1024 * 1024,
        description="Maximum bytes buffered per source transfer chunk.",
    )
    source_http_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        le=600,
        description="Timeout in seconds for each outbound HTTP source request.",
    )
    source_http_max_redirects: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum redirects followed when resolving an HTTP source.",
    )
    source_http_allowed_ports: tuple[int, ...] = Field(
        default=(80, 443), description="Destination TCP ports allowed for HTTP source URLs."
    )
    source_plugin_options: dict[str, dict[str, JsonValue]] = Field(
        default_factory=dict, description="Per-plugin source configuration, keyed by plugin name."
    )

    # Bounded POST rate limit for expensive routes, applied before auth.
    rate_limit_enabled: bool = Field(
        default=True, description="Apply bounded in-memory rate limiting to expensive HTTP routes."
    )
    rate_limit_trusted_proxy_cidrs: tuple[str, ...] = Field(
        default=(),
        description=(
            "Proxy CIDRs allowed to supply X-Forwarded-For for rate limiting. "
            "Only configure proxies that overwrite or append the connecting client address."
        ),
    )

    # JSON map: {"tenant-id": {"enabled_parsers": "markitdown,docling", ...}}
    tenant_plugin_policies: str | None = Field(
        default=None, description="JSON tenant-to-plugin policy map used to restrict plugin access."
    )
    # JSON map from authenticated HTTP Basic usernames to tenant IDs. The
    # X-Docpipe-Tenant-Id request header is informational and is never trusted.
    tenant_identity_map: dict[str, str] = Field(
        default_factory=dict,
        description="Maps authenticated Basic Auth usernames to tenant IDs.",
    )

    # Security
    # Set DOCPIPE_ALLOW_PRIVATE_URLS=true in environments where document sources
    # may resolve to private/internal network addresses (e.g. Docker Compose where
    # MinIO or other storage runs on the same network). Disabled by default to
    # prevent SSRF in public deployments.
    allow_private_urls: bool = Field(
        default=False,
        description="Permit private or loopback source URLs; enable only for trusted deployments.",
    )

    @field_validator("rate_limit_trusted_proxy_cidrs")
    @classmethod
    def validate_rate_limit_trusted_proxy_cidrs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize configured proxy networks and reject malformed entries."""
        try:
            return tuple(str(ipaddress.ip_network(cidr, strict=False)) for cidr in value)
        except ValueError as error:
            raise ValueError(
                "rate_limit_trusted_proxy_cidrs must contain valid IP CIDRs"
            ) from error

    # Speech-to-text (POST /transcribe)
    # openai: Whisper via OPENAI_API_KEY | vibevoice: local GPU (pip install VibeVoice)
    # vibevoice_remote: proxy to another docpipe with VibeVoice loaded
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
        default=8192, description="Maximum generated tokens for local VibeVoice transcription."
    )
    vibevoice_service_url: str | None = Field(
        default=None, description="Base URL for a remote Docpipe VibeVoice service."
    )
    vibevoice_remote_timeout: int = Field(
        default=600, description="Remote transcription request timeout in seconds."
    )

    # Phoenix eval tracing (optional — install arize-phoenix)
    phoenix_enabled: bool = Field(
        default=False, description="Enable optional Phoenix tracing for RAG and evaluation runs."
    )
    phoenix_collector_endpoint: str | None = Field(
        default=None, description="Phoenix collector endpoint used when Phoenix tracing is enabled."
    )

    # Optional control-plane database (admin users, audit, job history).
    # Off by default for SDK/library embeds; enable in Docker with SQLite.
    control_db_enabled: bool = Field(
        default=False,
        description="Enable the control-plane database for users, audit events, and job history.",
    )
    control_db_url: str | None = Field(
        default=None,
        description="SQLAlchemy URL. Defaults to SQLite at control_db_path when enabled.",
    )
    control_db_path: Path = Field(
        default=Path("/data/docpipe.db"),
        description="SQLite file path when control_db_url is unset.",
    )
    control_db_auto_migrate: bool = Field(
        default=True,
        description="Apply pending control-database migrations during application startup.",
    )

    # Admin panel at GET /admin (requires control_db_enabled).
    admin_panel_enabled: bool = Field(
        default=True,
        description="Expose the administrative web panel when the control database is enabled.",
    )

    # What to persist in the control DB (all off by default; opt-in per deployment).
    persist_audit_events: bool = Field(
        default=False,
        description="Persist security and administrative audit events in the control database.",
    )
    persist_ingest_jobs: bool = Field(
        default=False,
        description="Persist ingestion job state and history in the control database.",
    )
    persist_plugin_resolutions: bool = Field(
        default=False, description="Persist plugin resolution decisions in the control database."
    )

    # Seeded superuser when control DB is first initialized.
    admin_username: str | None = Field(
        default=None,
        description="Defaults to DOCPIPE_USERNAME when unset.",
    )
    admin_password: str | None = Field(
        default=None,
        description="Defaults to DOCPIPE_PASSWORD when unset.",
    )
    admin_email: str = Field(
        default="admin@localhost",
        description="Email address assigned to the seeded initial administrator.",
    )

    # Authentication
    # HTTP Basic Auth protecting all API endpoints and the web UI.
    # Disable entirely with DOCPIPE_AUTH_ENABLED=false for trusted internal networks.
    # When control_db_enabled=true, credentials are validated against admin_users.
    auth_enabled: bool = Field(
        default=True, description="Require HTTP Basic authentication for protected server routes."
    )
    username: str = Field(
        default="admin",
        description="HTTP Basic username when control-database authentication is disabled.",
    )
    password: str = Field(
        default="",
        description="HTTP Basic password outside control-database auth; configure a strong secret.",
    )

    def resolved_admin_username(self) -> str:
        return self.admin_username or self.username

    def resolved_admin_password(self) -> str:
        return self.admin_password or self.password

    def resolved_control_db_url(self) -> str | None:
        if not self.control_db_enabled:
            return None
        if self.control_db_url:
            return self.control_db_url
        path = self.control_db_path.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.resolve()}"
