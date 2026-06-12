"""POST /rag/query and /rag/stream schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from docpipe.core.types import TokenUsage
from docpipe.schemas.base import ApiResponse
from docpipe.schemas.common import (
    MetadataFiltersFields,
    TableNameFieldMixin,
    VectorBackendFields,
)


class ChatMessage(ApiResponse):
    """A single turn in multi-turn RAG conversation history."""

    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Speaker role.",
    )
    content: str = Field(..., min_length=1, description="Message text.")


class RAGQueryRequest(TableNameFieldMixin, VectorBackendFields, MetadataFiltersFields):
    """Retrieval-augmented generation query."""

    question: str = Field(..., min_length=1, description="User question to answer.")
    connection_string: str = Field(..., min_length=1, description="Vector store connection string.")
    embedding_provider: str = Field(..., min_length=1, description="Embedding provider name.")
    embedding_model: str = Field(..., min_length=1, description="Embedding model id.")
    llm_provider: str = Field(..., min_length=1, description="LLM provider name.")
    llm_model: str = Field(..., min_length=1, description="LLM model id.")
    api_key: str | None = Field(default=None, description="Optional LLM API key.")
    embedding_api_key: str | None = Field(
        default=None,
        description="Optional embedding API key.",
    )
    strategy: str | None = Field(
        default=None,
        description="Retrieval strategy override (naive, hybrid, etc.).",
    )
    preset: str | None = Field(
        default=None,
        description="Runtime preset: fast, balanced, quality, or agents.",
        examples=["balanced"],
    )
    lightrag_working_dir: str | None = Field(
        default=None,
        description="Working directory when using LightRAG strategy.",
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Chunks to retrieve.")
    max_chunks_per_source: int = Field(
        default=2,
        ge=1,
        description="Cap chunks per distinct source document.",
    )
    system_prompt: str = Field(
        ...,
        min_length=1,
        description="Application-owned answer prompt; must include {context} and {question}.",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation turns for multi-turn RAG.",
    )
    hyde_prompt: str | None = Field(default=None, description="Custom HyDE expansion prompt.")
    multi_query_prompt: str | None = Field(
        default=None,
        description="Custom multi-query expansion prompt.",
    )
    auto_strategy_prompt: str | None = Field(
        default=None,
        description="Custom prompt for automatic strategy selection.",
    )
    multi_query_count: int = Field(default=3, ge=1, le=10, description="Multi-query variants.")
    parent_window_size: int = Field(
        default=3,
        ge=0,
        description="Parent-document window for parent retriever.",
    )
    hybrid_bm25_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="BM25 weight in hybrid retrieval (remainder is dense).",
    )
    reranker: str = Field(default="none", description="Reranker plugin name or 'none'.")
    reranker_model: str | None = Field(default=None, description="Reranker model override.")
    rerank_top_n: int | None = Field(default=None, ge=1, description="Post-rerank chunk limit.")
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="OpenAI-compatible structured output schema.",
    )


class RAGChunkResponse(ApiResponse):
    """A retrieved chunk included in the RAG answer."""

    content: str = Field(..., description="Chunk text.")
    score: float = Field(..., description="Retrieval relevance score.")
    source: str = Field(..., description="Originating document source.")
    page: int | None = Field(default=None, description="Page number when available.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata.")


class RAGQueryResponse(ApiResponse):
    """Completed RAG query result."""

    query: str = Field(..., description="Original user question.")
    answer: str = Field(..., description="LLM-generated answer.")
    strategy: str = Field(..., description="Retrieval strategy that was used.")
    chunks: list[RAGChunkResponse] = Field(default_factory=list, description="Retrieved chunks.")
    sources: list[str] = Field(default_factory=list, description="Distinct source identifiers.")
    timing_seconds: float = Field(..., ge=0, description="End-to-end latency in seconds.")
    usage: TokenUsage | None = Field(default=None, description="Token usage when reported.")
