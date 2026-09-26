"""POST /ingest schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from docpipe.config.plugin_options import SourcePluginOptions
from docpipe.schemas.base import ApiResponse
from docpipe.schemas.common import TableNameFieldMixin, VectorBackendFields


class IngestRequest(TableNameFieldMixin, VectorBackendFields):
    """Ingest a document into a vector collection."""

    source: str = Field(
        ...,
        min_length=1,
        description="File path or URL to ingest (not raw bytes).",
        examples=["/data/manual.pdf"],
    )
    source_plugin: SourcePluginOptions | None = Field(
        default=None,
        description="Namespaced source plugin options; provider must match the source URI scheme.",
    )
    connection_string: str | None = Field(
        default=None, min_length=1, description="Legacy vector store connection string."
    )
    embedding_provider: str = Field(..., min_length=1, description="Embedding provider name.")
    embedding_model: str = Field(..., min_length=1, description="Embedding model id.")
    api_key: str | None = Field(
        default=None,
        description="Optional per-request embedding API key.",
    )
    parser: str | None = Field(default=None, description="Parser plugin override.")
    tier: str | None = Field(default=None, description="Parser tier override.")
    preset: str | None = Field(
        default=None,
        description="Runtime preset: fast, balanced, quality, or agents.",
        examples=["balanced"],
    )
    chunker: str | None = Field(default=None, description="Chunker plugin override.")
    chunk_method: str = Field(default="default", description="Chunking method name.")
    chunk_size: int = Field(
        default=1000,
        ge=64,
        le=32000,
        description="Target chunk size in tokens.",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Overlap between adjacent chunks.",
    )
    ingest_mode: Literal["chunks", "extractions", "both"] = Field(
        default="both",
        description="Whether to store raw chunks, extractions, or both.",
    )
    incremental: bool = Field(
        default=False,
        description="Skip re-ingest when source hash is unchanged.",
    )
    incremental_failure_mode: Literal["fail_closed", "legacy_best_effort"] = Field(
        default="fail_closed",
        description=(
            "Fail when duplicate state is unavailable, or explicitly preserve the "
            "deprecated fail-open behavior."
        ),
    )
    write_batch_size: int = Field(
        default=64,
        ge=1,
        le=10_000,
        description="Maximum records submitted in one vector write.",
    )
    max_in_flight: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Maximum concurrent embedding/write batches.",
    )
    chunk_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata attached to every chunk.",
    )
    graph_index: bool = Field(
        default=False,
        description="When true, also sync parsed text into a LightRAG working directory.",
    )
    lightrag_working_dir: str | None = Field(
        default=None,
        description="LightRAG on-disk directory; required when graph_index is true.",
    )


class IngestResponse(ApiResponse):
    """Ingestion outcome."""

    source: str = Field(..., description="Ingested source path or URL.")
    chunks_ingested: int = Field(..., ge=0, description="New chunks written.")
    skipped: int = Field(default=0, ge=0, description="Chunks skipped (incremental mode).")
    table_name: str = Field(..., description="Target collection name.")
    table_created: bool = Field(..., description="True when the collection was created.")
    lightrag_synced: bool = Field(
        default=False,
        description="True when parsed text was inserted into LightRAG.",
    )
