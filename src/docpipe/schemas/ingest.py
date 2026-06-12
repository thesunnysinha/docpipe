"""POST /ingest schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from docpipe.schemas.common import TableNameFieldMixin, VectorBackendFields


class IngestRequest(TableNameFieldMixin, VectorBackendFields):
    source: str
    connection_string: str
    embedding_provider: str
    embedding_model: str
    api_key: str | None = None
    parser: str | None = None
    tier: str | None = None
    preset: str | None = None
    chunker: str | None = None
    chunk_method: str = "default"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_mode: str = "both"
    incremental: bool = False
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    source: str
    chunks_ingested: int
    skipped: int = 0
    table_name: str
    table_created: bool
