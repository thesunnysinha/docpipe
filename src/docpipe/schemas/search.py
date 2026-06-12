"""POST /search schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from docpipe.schemas.base import ApiResponse
from docpipe.schemas.common import (
    MetadataFiltersFields,
    TableNameFieldMixin,
    VectorBackendFields,
)


class SearchRequest(TableNameFieldMixin, VectorBackendFields, MetadataFiltersFields):
    """Similarity search against an ingested vector collection."""

    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language search query.",
    )
    connection_string: str = Field(
        ...,
        min_length=1,
        description="Database connection string for the vector store.",
    )
    embedding_provider: str = Field(..., min_length=1, description="Embedding provider name.")
    embedding_model: str = Field(..., min_length=1, description="Embedding model id.")
    api_key: str | None = Field(
        default=None,
        description="Optional per-request embedding API key.",
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Maximum hits to return.")


class SearchResultItem(ApiResponse):
    """A single vector similarity search hit."""

    content: str = Field(..., description="Chunk text content.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk metadata stored at ingest time.",
    )
    score: float = Field(..., description="Similarity score (higher is more similar).")


class SearchResponse(ApiResponse):
    """Ranked search results."""

    results: list[SearchResultItem] = Field(
        default_factory=list,
        description="Hits ordered by descending similarity.",
    )
