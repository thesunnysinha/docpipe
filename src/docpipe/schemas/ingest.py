"""POST /ingest schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

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
    connection_string: str = Field(..., min_length=1, description="Vector store connection string.")
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
    chunk_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata attached to every chunk.",
    )


class IngestResponse(ApiResponse):
    """Ingestion outcome."""

    source: str = Field(..., description="Ingested source path or URL.")
    chunks_ingested: int = Field(..., ge=0, description="New chunks written.")
    skipped: int = Field(default=0, ge=0, description="Chunks skipped (incremental mode).")
    table_name: str = Field(..., description="Target collection name.")
    table_created: bool = Field(..., description="True when the collection was created.")
