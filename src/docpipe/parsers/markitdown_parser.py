"""MarkItDown adapter for lightweight document → Markdown conversion."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import DocumentFormat, PageContent, ParsedDocument

FORMAT_MAP: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".doc": DocumentFormat.DOCX,
    ".xlsx": DocumentFormat.XLSX,
    ".xls": DocumentFormat.XLSX,
    ".pptx": DocumentFormat.PPTX,
    ".ppt": DocumentFormat.PPTX,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".md": DocumentFormat.MARKDOWN,
    ".txt": DocumentFormat.TEXT,
    ".csv": DocumentFormat.TEXT,
    ".json": DocumentFormat.TEXT,
    ".xml": DocumentFormat.TEXT,
    ".png": DocumentFormat.IMAGE,
    ".jpg": DocumentFormat.IMAGE,
    ".jpeg": DocumentFormat.IMAGE,
    ".gif": DocumentFormat.IMAGE,
    ".webp": DocumentFormat.IMAGE,
    ".bmp": DocumentFormat.IMAGE,
    ".tiff": DocumentFormat.IMAGE,
    ".wav": DocumentFormat.AUDIO,
    ".mp3": DocumentFormat.AUDIO,
    ".m4a": DocumentFormat.AUDIO,
    ".mp4": DocumentFormat.VIDEO,
    ".zip": DocumentFormat.TEXT,
}


class MarkItDownParser:
    """Document parser using Microsoft MarkItDown."""

    name: str = "markitdown"

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ParserNotInstalledError(
                "MarkItDown is not installed. Install with: pip install docpipe-sdk[markitdown]"
            )
        from markitdown import MarkItDown

        self._converter = MarkItDown(**options)

    def _convert_source(self, source: str, **kwargs: Any) -> Any:
        """Convert a file path or URL to MarkItDown result."""
        if source.startswith(("http://", "https://")):
            return self._converter.convert(source, **kwargs)

        path = Path(source)
        if path.exists():
            return self._converter.convert_local(path, **kwargs)

        # Allow MarkItDown to resolve relative paths / permissive convert().
        return self._converter.convert(source, **kwargs)

    def _result_to_parsed(self, source: str, result: Any) -> ParsedDocument:
        markdown = getattr(result, "markdown", "") or ""
        text = getattr(result, "text_content", "") or markdown
        title = getattr(result, "title", None)

        metadata: dict[str, Any] = {"parser": self.name}
        if title:
            metadata["title"] = title

        pages: list[PageContent] = []
        if text.strip():
            pages = [PageContent(page_number=1, text=text)]

        return ParsedDocument(
            source=source,
            format=self._detect_format(source),
            text=text,
            markdown=markdown or text,
            metadata=metadata,
            pages=pages,
            raw=result,
        )

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Parse a single document."""
        try:
            result = self._convert_source(source, **kwargs)
        except Exception as e:
            raise ParseError(f"Failed to parse '{source}' with MarkItDown: {e}") from e
        return self._result_to_parsed(source, result)

    async def aparse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Async variant — runs sync parse in a thread."""
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        """Parse multiple documents sequentially."""
        return [self.parse(source, **kwargs) for source in sources]

    @classmethod
    def is_available(cls) -> bool:
        """Check if markitdown is installed."""
        try:
            import markitdown  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Return supported format strings."""
        return [
            "pdf",
            "docx",
            "xlsx",
            "pptx",
            "html",
            "image",
            "audio",
            "video",
            "text",
            "markdown",
            "csv",
            "json",
            "xml",
            "zip",
        ]

    @staticmethod
    def _detect_format(source: str) -> DocumentFormat:
        suffix = Path(urlparse(source).path if source.startswith("http") else source).suffix.lower()
        return FORMAT_MAP.get(suffix, DocumentFormat.TEXT)
