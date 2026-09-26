"""Shared fields and mixins for API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.core.types import validate_table_name
from docpipe.schemas.base import ApiRequest


class VectorBackendFields(ApiRequest):
    """Optional per-request vector store overrides."""

    vector_store: VectorStoreOptions | None = Field(
        default=None,
        description=(
            "Namespaced vector plugin configuration. The selected provider "
            "validates its options after plugin policy checks."
        ),
    )
    vector_backend: str | None = Field(
        default=None,
        description="Vector backend override: pgvector or turbovec.",
        examples=["pgvector"],
    )
    turbovec_index_dir: str | None = Field(
        default=None,
        description="Directory for on-disk TurboVec indexes.",
    )

    @model_validator(mode="after")
    def require_legacy_connection(self) -> VectorBackendFields:
        """Keep legacy requests strict while allowing new provider envelopes."""
        if self.vector_store is None and not getattr(self, "connection_string", None):
            raise ValueError("connection_string is required without vector_store")
        return self


class TableNameFieldMixin(ApiRequest):
    """PostgreSQL table/collection name with identifier validation."""

    table_name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="pgvector collection name (valid PostgreSQL identifier).",
        examples=["documents"],
    )

    _validate_table_name = field_validator("table_name")(validate_table_name)


class EmbeddingConnectionFields(ApiRequest):
    """Connection + embedding model fields shared by ingest/search/RAG."""

    connection_string: str = Field(
        ...,
        min_length=1,
        description="Database connection string for the vector store.",
    )
    embedding_provider: str = Field(
        ...,
        min_length=1,
        description="Embedding provider registry name.",
        examples=["openai"],
    )
    embedding_model: str = Field(
        ...,
        min_length=1,
        description="Embedding model identifier.",
        examples=["text-embedding-3-small"],
    )
    api_key: str | None = Field(
        default=None,
        description="Optional per-request API key for the embedding provider.",
    )


class MetadataFiltersFields(ApiRequest):
    """Optional pgvector metadata filters."""

    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata key/value filters applied during retrieval.",
    )
