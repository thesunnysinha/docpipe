"""Shared Pydantic models for docpipe."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DocumentFormat(str, Enum):
    """Supported document formats."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    HTML = "html"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"
    MARKDOWN = "markdown"


class PageContent(BaseModel):
    """Content from a single page of a parsed document."""

    page_number: int
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """Intermediate representation produced by any parser."""

    source: str
    format: DocumentFormat
    text: str
    markdown: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    pages: list[PageContent] = Field(default_factory=list)
    raw: Any = Field(default=None, exclude=True)


class SourceSpan(BaseModel):
    """Character-level grounding back to source text."""

    start: int
    end: int


class ExtractionResult(BaseModel):
    """Standardized extraction output from any extractor."""

    entity_class: str
    text: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_span: SourceSpan | None = None
    confidence: float | None = None


class ExtractionSchema(BaseModel):
    """Defines what to extract from text."""

    description: str
    examples: list[dict[str, Any]] = Field(default_factory=list)
    entity_classes: list[str] = Field(default_factory=list)
    model_id: str
    output_model: Any = Field(
        default=None,
        description="Pydantic model class for LangChain structured output",
        exclude=True,
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    """Full pipeline output: parsed document + extractions."""

    source: str
    parsed: ParsedDocument
    extractions: list[ExtractionResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def validate_table_name(v: str) -> str:
    """Validate that a string is a safe PostgreSQL identifier."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
        raise ValueError(
            "table_name must be a valid PostgreSQL identifier (letters, digits, underscores only)"
        )
    return v


class IngestionConfig(BaseModel):
    """Configuration for the ingestion pipeline."""

    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    # Optional per-request API key for the embedding provider.
    # Falls back to the provider's standard environment variable when None.
    embedding_api_key: str | None = None
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_mode: Literal["chunks", "extractions", "both"] = "both"
    incremental: bool = False
    # Domain-specific chunking
    chunk_method: Literal[
        "default", "paper", "laws", "book", "qa", "manual", "table", "presentation"
    ] = "default"
    # Contextual chunk injection
    contextual_injection: bool = False
    contextual_llm_provider: str = "openai"
    contextual_llm_model: str = "gpt-4o-mini"
    # Vector store backend (per-request override; server default from DOCPIPE_VECTOR_BACKEND)
    vector_backend: Literal["pgvector", "turbovec"] | None = None
    turbovec_index_dir: str | None = None
    # Merged into every chunk's vector metadata (e.g. document_id, title for citations).
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)

    _validate_table_name = field_validator("table_name")(validate_table_name)


class TokenUsage(BaseModel):
    """LLM token usage from provider responses."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class IngestionResult(BaseModel):
    """Result of an ingestion operation."""

    source: str
    chunks_ingested: int
    skipped: int = 0
    table_name: str
    table_created: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeleteRequest(BaseModel):
    """Request to delete chunks by source from a pgvector table."""

    connection_string: str
    table_name: str
    source: str | None = None
    source_contains: str | None = None
    match_mode: Literal["exact", "contains"] = "exact"
    vector_backend: Literal["pgvector", "turbovec"] | None = None
    turbovec_index_dir: str | None = None
    # Required when vector_backend=turbovec (to load the on-disk index for delete)
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None

    @field_validator("table_name")
    @classmethod
    def _validate_table_name(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
            raise ValueError(
                "table_name must be a valid PostgreSQL identifier"
                " (letters, digits, underscores only)"
            )
        return v

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


class DeleteResponse(BaseModel):
    """Result of a delete operation."""

    table_name: str
    source: str
    chunks_deleted: int


# ---------------------------------------------------------------------------
# RAG types
# ---------------------------------------------------------------------------


class RAGConfig(BaseModel):
    """Configuration for the RAG query pipeline."""

    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
    # Per-request API keys. When None, falls back to provider env vars.
    embedding_api_key: str | None = None
    llm_provider: str
    llm_model: str
    llm_api_key: str | None = None
    strategy: Literal["naive", "hyde", "multi_query", "parent_document", "hybrid", "auto"] = "naive"
    top_k: int = 5
    # Strategy-specific
    hyde_prompt: str | None = None
    multi_query_count: int = 3
    parent_window_size: int = 3
    hybrid_bm25_weight: float = 0.5
    # Reranking
    reranker: Literal["none", "flashrank", "cohere"] = "none"
    reranker_model: str | None = None
    rerank_top_n: int | None = None
    # Generation
    system_prompt: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)
    output_model: Any = Field(
        default=None,
        description="Pydantic model class for structured RAG output",
        exclude=True,
    )
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="JSON schema dict for structured output (REST-friendly)",
    )
    stream: bool = False
    # Semantic query cache
    cache_enabled: bool = False
    cache_similarity_threshold: float = 0.95
    cache_max_size: int = 100
    # Metadata filtering
    filters: dict[str, Any] = Field(default_factory=dict)
    vector_backend: Literal["pgvector", "turbovec"] | None = None
    turbovec_index_dir: str | None = None

    _validate_table_name = field_validator("table_name")(validate_table_name)


class RAGChunk(BaseModel):
    """A single retrieved chunk with provenance."""

    content: str
    score: float
    source: str
    page: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGResult(BaseModel):
    """Output of a RAGPipeline.query() call."""

    query: str
    answer: str
    strategy: str
    chunks: list[RAGChunk]
    sources: list[str]
    timing_seconds: float
    usage: TokenUsage | None = None
    structured: Any = Field(default=None, exclude=True)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluation types
# ---------------------------------------------------------------------------


class EvalQuestion(BaseModel):
    """A single question with ground truth for RAG evaluation."""

    question: str
    expected_answer: str
    expected_sources: list[str] = Field(default_factory=list)


class EvalConfig(BaseModel):
    """Configuration for the evaluation pipeline."""

    rag_config: RAGConfig
    questions: list[EvalQuestion]
    metrics: list[Literal["hit_rate", "mrr", "faithfulness", "answer_similarity"]] = Field(
        default_factory=lambda: ["hit_rate", "answer_similarity"]
    )


class EvalMetrics(BaseModel):
    """Aggregate evaluation metrics."""

    hit_rate: float | None = None
    mrr: float | None = None
    faithfulness: float | None = None
    answer_similarity: float | None = None
    per_question: list[dict[str, Any]] = Field(default_factory=list)


class EvalResult(BaseModel):
    """Output of an EvalPipeline.run() call."""

    metrics: EvalMetrics
    num_questions: int
    timing_seconds: float
    metadata: dict[str, Any] = Field(default_factory=dict)
