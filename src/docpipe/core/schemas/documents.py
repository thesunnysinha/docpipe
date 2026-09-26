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
    """Content from a single page of a parsed document."""

    page_number: int = Field(...)
    text: str = Field(...)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """Intermediate representation produced by any parser."""

    source: str = Field(...)
    format: DocumentFormat = Field(...)
    text: str = Field(...)
    markdown: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)
    pages: list[PageContent] = Field(default_factory=list)
    raw: Any = Field(default=None, exclude=True)
