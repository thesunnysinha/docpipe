"""Shared fields and mixins for API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from docpipe.core.types import validate_table_name


class VectorBackendFields(BaseModel):
    """Optional per-request vector store overrides."""

    vector_backend: str | None = None
    turbovec_index_dir: str | None = None


class TableNameFieldMixin(BaseModel):
    """PostgreSQL table/collection name with identifier validation."""

    table_name: str

    _validate_table_name = field_validator("table_name")(validate_table_name)


class EmbeddingConnectionFields(BaseModel):
    """Connection + embedding model fields shared by ingest/search/RAG."""

    connection_string: str
    embedding_provider: str
    embedding_model: str
    api_key: str | None = None


class MetadataFiltersFields(BaseModel):
    """Optional pgvector metadata filters."""

    filters: dict[str, Any] = Field(default_factory=dict)
