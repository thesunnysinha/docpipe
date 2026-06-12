"""DELETE /ingest request and response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from docpipe.schemas.base import ApiRequest, ApiResponse
from docpipe.schemas.common import TableNameFieldMixin


class DeleteRequest(TableNameFieldMixin, ApiRequest):
    """Remove ingested chunks for a source from a vector collection."""

    connection_string: str = Field(
        ...,
        min_length=1,
        description="PostgreSQL or vector-store connection string.",
        examples=["postgresql://user:pass@localhost:5432/docpipe"],
    )
    source: str | None = Field(
        default=None,
        description="Exact source path or URL to delete when match_mode is 'exact'.",
        examples=["/data/report.pdf"],
    )
    source_contains: str | None = Field(
        default=None,
        description="Substring match for sources when match_mode is 'contains'.",
        examples=["report"],
    )
    match_mode: Literal["exact", "contains"] = Field(
        default="exact",
        description="Whether to match source exactly or by substring.",
    )
    vector_backend: Literal["pgvector", "turbovec"] | None = Field(
        default=None,
        description="Override vector backend; defaults to server configuration.",
    )
    turbovec_index_dir: str | None = Field(
        default=None,
        description="On-disk TurboVec index directory (required for turbovec deletes).",
    )
    embedding_provider: str | None = Field(
        default=None,
        description="Embedding provider name when vector_backend is turbovec.",
    )
    embedding_model: str | None = Field(
        default=None,
        description="Embedding model name when vector_backend is turbovec.",
    )
    embedding_api_key: str | None = Field(
        default=None,
        description="Optional API key for the embedding provider.",
    )

    @model_validator(mode="after")
    def _validate_source_fields(self) -> DeleteRequest:
        if self.match_mode == "contains":
            if not self.source_contains:
                raise ValueError("source_contains is required when match_mode='contains'")
            if self.source:
                raise ValueError("source must not be set when match_mode='contains'")
        elif not self.source:
            raise ValueError("source is required when match_mode='exact'")
        return self


class DeleteResponse(ApiResponse):
    """Outcome of a vector-store delete operation."""

    table_name: str = Field(..., description="Collection/table that was modified.")
    source: str = Field(..., description="Source identifier that was matched for deletion.")
    chunks_deleted: int = Field(..., ge=0, description="Number of chunks removed.")
