"""PyMuPDF4LLM adapter for fast CPU PDF parsing."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import PageContent, ParsedDocument
from docpipe.parsers.markitdown_parser import MarkItDownParser


class PyMuPDFParser:
    """Parse PDF documents into Markdown with PyMuPDF4LLM.

    This optional CPU backend advertises PDF support and represents non-empty
    output as one aggregate page. Its AGPL-3.0 license is exposed on the class
    for callers evaluating parser licensing.
    """

    name = "pymupdf"
    license = "AGPL-3.0"
    requires_gpu = False

    def __init__(self, **options: Any) -> None:
        """Create the adapter and retain options passed to ``to_markdown``.

        Raises:
            ParserNotInstalledError: If PyMuPDF4LLM is unavailable.
        """
        if not self.is_available():
            raise ParserNotInstalledError(
                "PyMuPDF4LLM is not installed. Install with: pip install docpipe-sdk[pymupdf]"
            )
        self._options = options

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Convert one source to Markdown using PyMuPDF4LLM.

        Per-call options override constructor options. The detected source
        format is recorded in the result; this adapter advertises PDF only.

        Raises:
            ParserNotInstalledError: If PyMuPDF4LLM cannot be imported.
            ParseError: If the upstream conversion raises an exception.
        """
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
        """Run :meth:`parse` in a worker thread and return its result or error."""
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        """Parse sources sequentially; the first parse error stops the batch."""
        return [self.parse(s, **kwargs) for s in sources]

    @classmethod
    def is_available(cls) -> bool:
        """Return whether the optional ``pymupdf4llm`` package imports."""
        try:
            import pymupdf4llm  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Return the format names advertised by this PDF-specific adapter."""
        return ["pdf"]
