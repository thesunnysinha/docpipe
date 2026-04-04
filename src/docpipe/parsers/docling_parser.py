"""Docling adapter for document parsing."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import DocumentFormat, PageContent, ParsedDocument

logger = logging.getLogger(__name__)

FORMAT_MAP: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".xlsx": DocumentFormat.XLSX,
    ".pptx": DocumentFormat.PPTX,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".md": DocumentFormat.MARKDOWN,
    ".txt": DocumentFormat.TEXT,
    ".png": DocumentFormat.IMAGE,
    ".jpg": DocumentFormat.IMAGE,
    ".jpeg": DocumentFormat.IMAGE,
    ".tiff": DocumentFormat.IMAGE,
    ".bmp": DocumentFormat.IMAGE,
    ".webp": DocumentFormat.IMAGE,
}


class DoclingParser:
    """Document parser using IBM Docling."""

    name: str = "docling"

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ParserNotInstalledError(
                "Docling is not installed. Install with: pip install docpipe[docling]"
            )
        from docling.document_converter import DocumentConverter

        self._converter = DocumentConverter(**options)

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Parse a single document."""
        try:
            result = self._converter.convert(source, **kwargs)
        except Exception as e:
            raise ParseError(f"Failed to parse '{source}': {e}") from e

        doc = result.document
        pages: list[PageContent] = []
        if hasattr(doc, "pages") and doc.pages:
            for i, page in enumerate(doc.pages):
                page_text = page.export_to_text() if hasattr(page, "export_to_text") else ""
                pages.append(PageContent(page_number=i + 1, text=page_text))

        return ParsedDocument(
            source=source,
            format=self._detect_format(source),
            text=doc.export_to_text(),
            markdown=doc.export_to_markdown(),
            metadata={"status": result.status.name},
            pages=pages,
            raw=doc,
        )

    async def aparse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Async variant - runs sync parse in a thread."""
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        """Parse multiple documents using Docling's batch conversion."""
        results = []
        for conv_result in self._converter.convert_all(sources, **kwargs):
            doc = conv_result.document
            results.append(
                ParsedDocument(
                    source=str(conv_result.input.file) if conv_result.input else "unknown",
                    format=self._detect_format(
                        str(conv_result.input.file) if conv_result.input else ""
                    ),
                    text=doc.export_to_text(),
                    markdown=doc.export_to_markdown(),
                    metadata={"status": conv_result.status.name},
                    raw=doc,
                )
            )
        return results

    def to_langchain_documents(self, parsed: ParsedDocument) -> list[Any]:
        """Convert ParsedDocument to LangChain Document objects."""
        from langchain_core.documents import Document as LCDocument

        if parsed.pages:
            return [
                LCDocument(
                    page_content=page.text,
                    metadata={**parsed.metadata, "page": page.page_number, "source": parsed.source},
                )
                for page in parsed.pages
                if page.text.strip()
            ]
        return [
            LCDocument(
                page_content=parsed.text,
                metadata={**parsed.metadata, "source": parsed.source},
            )
        ]

    @classmethod
    def is_available(cls) -> bool:
        """Check if docling is installed."""
        try:
            import docling  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Return supported format strings."""
        return [
            "pdf", "docx", "xlsx", "pptx", "html",
            "image", "audio", "video", "text", "markdown",
        ]

    @staticmethod
    def _detect_format(source: str) -> DocumentFormat:
        """Detect document format from file extension or URL."""
        suffix = Path(source).suffix.lower()
        return FORMAT_MAP.get(suffix, DocumentFormat.TEXT)
