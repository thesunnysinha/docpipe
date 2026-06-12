"""POST /collection/sources — distinct ingested sources in a vector collection."""

from __future__ import annotations

from pydantic import Field

from docpipe.schemas.base import ApiResponse
from docpipe.schemas.common import MetadataFiltersFields, TableNameFieldMixin, VectorBackendFields


class SourceSummary(ApiResponse):
    """Aggregated stats for one ingested source."""

    source: str = Field(..., description="Source path or URL.")
    chunk_count: int = Field(..., ge=0, description="Chunks stored for this source.")
    document_id: str | None = Field(default=None, description="Optional document id metadata.")
    document_title: str | None = Field(default=None, description="Optional human title.")


class ListSourcesRequest(TableNameFieldMixin, VectorBackendFields, MetadataFiltersFields):
    """List distinct sources in a vector collection."""

    connection_string: str = Field(..., min_length=1, description="Vector store connection string.")


class ListSourcesResponse(ApiResponse):
    """Sources present in a collection."""

    table_name: str = Field(..., description="Queried collection name.")
    sources: list[SourceSummary] = Field(
        default_factory=list,
        description="Per-source chunk counts.",
    )
    total_chunks: int = Field(default=0, ge=0, description="Total chunks in the collection.")
