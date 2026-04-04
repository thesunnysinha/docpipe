"""Shared Pydantic models for docpipe."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


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


class IngestionResult(BaseModel):
    """Result of an ingestion operation."""

    source: str
    chunks_ingested: int
    table_name: str
    table_created: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
