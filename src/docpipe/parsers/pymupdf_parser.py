"""PyMuPDF4LLM adapter for fast CPU PDF parsing."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import PageContent, ParsedDocument
from docpipe.parsers.markitdown_parser import MarkItDownParser


class PyMuPDFParser:
    """Document parser using PyMuPDF4LLM."""

    name = "pymupdf"
    license = "AGPL-3.0"
    requires_gpu = False

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ParserNotInstalledError(
                "PyMuPDF4LLM is not installed. Install with: pip install docpipe-sdk[pymupdf]"
            )
        self._options = options

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        try:
            import pymupdf4llm
        except ImportError as e:
            raise ParserNotInstalledError("pymupdf4llm not installed") from e
        try:
            markdown = pymupdf4llm.to_markdown(source, **{**self._options, **kwargs})
        except Exception as e:
            raise ParseError(f"Failed to parse '{source}' with PyMuPDF4LLM: {e}") from e
        text = markdown if isinstance(markdown, str) else str(markdown)
        pages = [PageContent(page_number=1, text=text)] if text.strip() else []
        return ParsedDocument(
            source=source,
            format=MarkItDownParser._detect_format(source),
            text=text,
            markdown=text,
            metadata={"parser": self.name},
            pages=pages,
        )

    async def aparse(self, source: str, **kwargs: Any) -> ParsedDocument:
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        return [self.parse(s, **kwargs) for s in sources]

    @classmethod
    def is_available(cls) -> bool:
        try:
            import pymupdf4llm  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        return ["pdf"]
