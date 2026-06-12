"""POST /rag/query and /rag/stream schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from docpipe.core.types import TokenUsage
from docpipe.schemas.common import (
    MetadataFiltersFields,
    TableNameFieldMixin,
    VectorBackendFields,
)


class RAGQueryRequest(TableNameFieldMixin, VectorBackendFields, MetadataFiltersFields):
    question: str
    connection_string: str
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    llm_model: str
    api_key: str | None = None
    embedding_api_key: str | None = None
    strategy: str | None = None
    preset: str | None = Field(
        default=None,
        description="Runtime preset: fast, balanced, quality, or agents",
        examples=["balanced"],
    )
    lightrag_working_dir: str | None = None
    top_k: int = 5
    max_chunks_per_source: int = 2
    system_prompt: str = Field(
        ...,
        min_length=1,
        description="Application-owned answer prompt; must include {context} and {question}.",
    )
    history: list[dict[str, str]] = Field(default_factory=list)
    hyde_prompt: str | None = None
    multi_query_prompt: str | None = None
    auto_strategy_prompt: str | None = None
    multi_query_count: int = 3
    parent_window_size: int = 3
    hybrid_bm25_weight: float = 0.5
    reranker: str = "none"
    reranker_model: str | None = None
    rerank_top_n: int | None = None
    response_format: dict[str, Any] | None = None


class RAGChunkResponse(BaseModel):
    content: str
    score: float
    source: str
    page: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    strategy: str
    chunks: list[RAGChunkResponse]
    sources: list[str]
    timing_seconds: float
    usage: TokenUsage | None = None
