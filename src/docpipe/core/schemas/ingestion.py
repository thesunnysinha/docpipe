"""Public ingestion configuration and result schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from docpipe.config.plugin_options import SourcePluginOptions, VectorStoreOptions
from docpipe.core.schemas.common import validate_table_name


class IngestionConfig(BaseModel):
    """Configuration for the ingestion pipeline."""

    connection_string: str | None = Field(default=None)
    table_name: str = Field(...)
    embedding_provider: str = Field(...)
    embedding_model: str = Field(...)
    # Optional per-request API key; falls back to provider environment variables.
    embedding_api_key: str | None = Field(default=None)
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    ingest_mode: Literal["chunks", "extractions", "both"] = Field(default="both")
    incremental: bool = Field(default=False)
    incremental_failure_mode: Literal["fail_closed", "legacy_best_effort"] = Field(
        default="fail_closed"
    )
    chunk_method: Literal[
        "default", "paper", "laws", "book", "qa", "manual", "table", "presentation"
    ] = Field(default="default")
    chunker: str = Field(default="recursive")
    contextual_injection: bool = Field(default=False)
    contextual_llm_provider: str = Field(default="openai")
    contextual_llm_model: str = Field(default="gpt-4o-mini")
    vector_backend: Literal["pgvector", "turbovec"] | None = Field(default=None)
    vector_store: VectorStoreOptions | None = Field(default=None)
    source_plugin: SourcePluginOptions | None = Field(default=None)
    turbovec_index_dir: str | None = Field(default=None)
    turbovec_bit_width: Literal[2, 3, 4] = Field(default=4)
    write_batch_size: int = Field(default=64, ge=1, le=10_000)
    max_in_flight: int = Field(default=4, ge=1, le=64)
    # Merged into every chunk's vector metadata for citations.
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)

    _validate_table_name = field_validator("table_name")(validate_table_name)

    @model_validator(mode="after")
    def require_legacy_connection(self) -> IngestionConfig:
        """Require the legacy DSN unless a namespaced provider is supplied."""
        if self.vector_store is None and not self.connection_string:
            raise ValueError("connection_string is required without vector_store")
        return self


class IngestionResult(BaseModel):
    """Result of an ingestion operation."""

    source: str = Field(...)
    chunks_ingested: int = Field(...)
    skipped: int = Field(default=0)
    table_name: str = Field(...)
    table_created: bool = Field(...)
    metadata: dict[str, Any] = Field(default_factory=dict)
