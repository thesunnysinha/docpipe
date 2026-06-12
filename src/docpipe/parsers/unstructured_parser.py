"""Unstructured.io partition adapter."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import PageContent, ParsedDocument
from docpipe.parsers.markitdown_parser import MarkItDownParser


class UnstructuredParser:
    """Document parser using unstructured partition."""

    name = "unstructured"
    license = "Apache-2.0"
    requires_gpu = False

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ParserNotInstalledError(
                "Unstructured is not installed. Install with: pip install docpipe-sdk[unstructured]"
            )
        self._options = options

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        try:
            from unstructured.partition.auto import partition
        except ImportError as e:
            raise ParserNotInstalledError("unstructured not installed") from e
        try:
            elements = partition(filename=source, **{**self._options, **kwargs})
        except Exception as e:
            raise ParseError(f"Unstructured failed on '{source}': {e}") from e
        parts: list[str] = []
        pages: list[PageContent] = []
        for i, el in enumerate(elements, start=1):
            text = str(el)
            if not text.strip():
                continue
            parts.append(text)
            pages.append(
                PageContent(
                    page_number=i,
                    text=text,
                    metadata={"category": getattr(el, "category", None)},
                )
            )
        full = "\n\n".join(parts)
        return ParsedDocument(
            source=source,
            format=MarkItDownParser._detect_format(source),
            text=full,
            markdown=full,
            metadata={"parser": self.name, "element_count": len(elements)},
            pages=pages,
            raw=elements,
        )

    async def aparse(self, source: str, **kwargs: Any) -> ParsedDocument:
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        return [self.parse(s, **kwargs) for s in sources]

    @classmethod
    def is_available(cls) -> bool:
        try:
            import unstructured  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        return [
            "pdf",
            "docx",
            "pptx",
            "xlsx",
            "html",
            "image",
            "text",
            "markdown",
            "csv",
            "json",
            "xml",
        ]
