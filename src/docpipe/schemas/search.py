"""POST /search schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from docpipe.schemas.common import (
    MetadataFiltersFields,
    TableNameFieldMixin,
    VectorBackendFields,
)


class SearchRequest(TableNameFieldMixin, VectorBackendFields, MetadataFiltersFields):
    query: str
    connection_string: str
    embedding_provider: str
    embedding_model: str
    api_key: str | None = None
    top_k: int = 10


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]
