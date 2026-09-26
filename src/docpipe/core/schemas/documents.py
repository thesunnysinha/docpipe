"""Parsed document and page schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

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
    """Text and parser metadata associated with one source page."""

    page_number: int = Field(..., description="Source page number as reported by the parser.")
    text: str = Field(..., description="Extracted text for this page; may be empty.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Parser-provided page metadata."
    )


class ParsedDocument(BaseModel):
    """Parser-neutral document representation shared by downstream workflows.

    ``raw`` may hold a backend-specific object for in-process consumers; it is
    excluded from serialized output because it may not be JSON serializable.
    """

    source: str = Field(..., description="Original source path, URL, or source identifier.")
    format: DocumentFormat = Field(..., description="Detected or selected source document format.")
    text: str = Field(..., description="Plain-text representation produced by the parser.")
    markdown: str = Field(
        default="", description="Markdown representation when the parser provides one."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Parser-specific document metadata."
    )
    pages: list[PageContent] = Field(
        default_factory=list, description="Page-level content when available."
    )
    raw: Any = Field(
        default=None,
        exclude=True,
        description="Optional backend object for in-process use; omitted from serialization.",
    )
