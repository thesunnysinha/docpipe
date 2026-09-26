"""Public ingestion configuration and result schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from docpipe.config.plugin_options import SourcePluginOptions, VectorStoreOptions
from docpipe.core.schemas.common import validate_table_name


class IngestionConfig(BaseModel):
    """Options controlling source ingestion, chunking, embedding, and writes.

    A provider-neutral ``vector_store`` may replace the legacy connection string;
    otherwise the legacy DSN is required by the model validator. Credentials are
    runtime inputs and should not be persisted in logs or serialized config.
    """

    connection_string: str | None = Field(
        default=None,
        description=(
            "Legacy vector database connection URL; optional when vector_store is supplied."
        ),
    )
    table_name: str = Field(..., description="Target vector collection or table name.")
    embedding_provider: str = Field(
        ..., description="Embedding provider registry name used to encode chunks."
    )
    embedding_model: str = Field(
        ..., description="Embedding model identifier compatible with the target index."
    )
    # Optional per-request API key; falls back to provider environment variables.
    embedding_api_key: str | None = Field(
        default=None,
        description=(
            "Optional provider credential; falls back to provider environment configuration."
        ),
    )
    chunk_size: int = Field(
        default=1000,
        description="Target chunk size interpreted by the selected chunker.",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Target overlap between adjacent chunks, interpreted by the selected chunker.",
    )
    ingest_mode: Literal["chunks", "extractions", "both"] = Field(
        default="both", description="Whether to persist chunks, extraction records, or both."
    )
    incremental: bool = Field(
        default=False,
        description="Use stored source state to skip unchanged input where supported.",
    )
    incremental_failure_mode: Literal["fail_closed", "legacy_best_effort"] = Field(
        default="fail_closed",
        description=(
            "Behavior when stored state cannot be read: reject the operation or use "
            "legacy best-effort handling."
        ),
    )
    chunk_method: Literal[
        "default", "paper", "laws", "book", "qa", "manual", "table", "presentation"
    ] = Field(
        default="default",
        description="Domain-specific chunking strategy passed to the configured chunker.",
    )
    chunker: str = Field(default="recursive", description="Registered chunker plugin name.")
    contextual_injection: bool = Field(
        default=False,
        description="Whether to enrich chunks with generated contextual text before embedding.",
    )
    contextual_llm_provider: str = Field(
        default="openai",
        description="LLM provider used for contextual enrichment when enabled.",
    )
    contextual_llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model used for contextual enrichment when enabled.",
    )
    vector_backend: Literal["pgvector", "turbovec"] | None = Field(
        default=None, description="Legacy vector backend selector retained for compatibility."
    )
    vector_store: VectorStoreOptions | None = Field(
        default=None, description="Provider-neutral vector plugin selection and options."
    )
    source_plugin: SourcePluginOptions | None = Field(
        default=None, description="Optional provider-neutral source plugin configuration."
    )
    turbovec_index_dir: str | None = Field(
        default=None, description="Filesystem directory for a local TurboVec index."
    )
    turbovec_bit_width: Literal[2, 3, 4] = Field(
        default=4, description="Quantization bit width selected for TurboVec storage."
    )
    write_batch_size: int = Field(
        default=64,
        ge=1,
        le=10_000,
        description="Maximum records submitted in one vector-store write batch.",
    )
    max_in_flight: int = Field(
        default=4, ge=1, le=64, description="Maximum concurrent vector-write batches."
    )
    # Merged into every chunk's vector metadata for citations.
    chunk_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata merged into each chunk record, commonly for filtering and citations.",
    )

    _validate_table_name = field_validator("table_name")(validate_table_name)

    @model_validator(mode="after")
    def require_legacy_connection(self) -> IngestionConfig:
        """Require the legacy DSN unless a namespaced provider is supplied."""
        if self.vector_store is None and not self.connection_string:
            raise ValueError("connection_string is required without vector_store")
        return self


class IngestionResult(BaseModel):
    """Summary of records and collection state after an ingestion operation."""

    source: str = Field(..., description="Source path, URL, or stable source identifier processed.")
    chunks_ingested: int = Field(
        ..., description="Number of chunks confirmed written to the vector store."
    )
    skipped: int = Field(
        default=0,
        description="Number of source documents skipped; a single-source run reports zero or one.",
    )
    table_name: str = Field(..., description="Vector collection or table receiving the records.")
    table_created: bool = Field(
        ...,
        description=(
            "Legacy success flag set after a nonempty write; true does not guarantee that "
            "the target collection or table was newly created."
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional ingestion diagnostics and source metadata."
    )
