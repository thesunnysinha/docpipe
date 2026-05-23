"""POST /collection/sources — distinct ingested sources in a vector collection."""

from __future__ import annotations

from pydantic import BaseModel, Field

from docpipe.schemas.common import MetadataFiltersFields, TableNameFieldMixin, VectorBackendFields


class SourceSummary(BaseModel):
    source: str
    chunk_count: int
    document_id: str | None = None
    document_title: str | None = None


class ListSourcesRequest(TableNameFieldMixin, VectorBackendFields, MetadataFiltersFields):
    connection_string: str


class ListSourcesResponse(BaseModel):
    table_name: str
    sources: list[SourceSummary] = Field(default_factory=list)
    total_chunks: int = 0
