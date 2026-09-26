"""RAG response-cache settings."""

from typing import Literal

from pydantic import Field

from docpipe.config.settings_sections.base import Settings


class RAGCacheSettings(Settings):
    """Optional Redis and bounded process-memory RAG cache configuration."""

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
