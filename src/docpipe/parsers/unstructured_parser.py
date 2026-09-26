"""Unstructured.io partition adapter."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import PageContent, ParsedDocument
from docpipe.parsers.markitdown_parser import MarkItDownParser


class UnstructuredParser:
    """Parse documents into text elements with Unstructured's partition API.

    Unstructured and its format-specific dependencies are optional. This
    adapter retains each non-empty element as a page-like result, and includes
    the original element sequence in ``ParsedDocument.raw``. Advertised formats
    do not guarantee that every corresponding system dependency is installed.
    """

    name = "unstructured"
    license = "Apache-2.0"
    requires_gpu = False

    def __init__(self, **options: Any) -> None:
        """Create the adapter and retain options for ``partition``.

        Raises:
            ParserNotInstalledError: If the optional ``unstructured`` package
                is unavailable.
        """
        if not self.is_available():
            raise ParserNotInstalledError(
                "Unstructured is not installed. Install with: pip install docpipe-sdk[unstructured]"
            )
        self._options = options

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Partition one local or approved HTTP(S) source into text elements.

        Per-call options override constructor options. Whitespace-only
        elements are omitted from ``text`` and ``pages``; page numbers retain
        the original one-based element positions. The result records the
        upstream element count, including elements omitted from text.

        Raises:
            ParserNotInstalledError: If Unstructured cannot be imported.
            ParseError: If the upstream partition operation raises an exception.
        """
        from docpipe.parsers.url_safety import assert_safe_http_source

        assert_safe_http_source(source)
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
        """Run :meth:`parse` in a worker thread and return its result or error."""
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        """Parse sources sequentially; the first parse error stops the batch."""
        return [self.parse(s, **kwargs) for s in sources]

    @classmethod
    def is_available(cls) -> bool:
        """Return whether the top-level optional ``unstructured`` package imports."""
        try:
            import unstructured  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Return advertised format names, not installed system capabilities."""
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
