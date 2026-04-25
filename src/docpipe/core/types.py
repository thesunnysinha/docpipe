"""Shared Pydantic models for docpipe."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

import re

from pydantic import BaseModel, Field, field_validator


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


class IngestionConfig(BaseModel):
    """Configuration for the ingestion pipeline."""

    connection_string: str
    table_name: str
    embedding_provider: str
    embedding_model: str
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
    source: str

    @field_validator("table_name")
    @classmethod
    def _validate_table_name(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
            raise ValueError("table_name must be a valid PostgreSQL identifier (letters, digits, underscores only)")
        return v


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
    llm_provider: str
    llm_model: str
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
    output_model: Any = Field(
        default=None,
        description="Pydantic model class for structured RAG output",
        exclude=True,
    )
    stream: bool = False
    # Semantic query cache
    cache_enabled: bool = False
    cache_similarity_threshold: float = 0.95
    cache_max_size: int = 100


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
