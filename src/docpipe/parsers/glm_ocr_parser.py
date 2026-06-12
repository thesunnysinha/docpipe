"""GLM-OCR adapter for document parsing."""

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
    ".png": DocumentFormat.IMAGE,
    ".jpg": DocumentFormat.IMAGE,
    ".jpeg": DocumentFormat.IMAGE,
    ".tiff": DocumentFormat.IMAGE,
    ".bmp": DocumentFormat.IMAGE,
    ".webp": DocumentFormat.IMAGE,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".md": DocumentFormat.MARKDOWN,
    ".txt": DocumentFormat.TEXT,
}


class GLMOCRParser:
    """Document parser using GLM-OCR (state-of-the-art multimodal OCR)."""

    name: str = "glm-ocr"

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ParserNotInstalledError(
                "GLM-OCR is not installed. Install with: pip install docpipe-sdk[glm-ocr]"
            )
        self._options = options
        self._ocr: Any = None

    def _get_ocr(self) -> Any:
        if self._ocr is None:
            from glmocr import GLMOCR

            from docpipe.config import get_settings

            settings = get_settings()
            opts = dict(self._options)
            if settings.model_cache_dir is not None:
                opts.setdefault("cache_dir", str(settings.model_cache_dir))
            self._ocr = GLMOCR(**opts)
        return self._ocr

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Parse a single document using GLM-OCR."""
        from docpipe.parsers.url_safety import assert_safe_http_source

        assert_safe_http_source(source)
        try:
            result = self._get_ocr().run(source, **kwargs)
        except Exception as e:
            raise ParseError(f"Failed to parse '{source}' with GLM-OCR: {e}") from e

        pages: list[PageContent] = []
        if hasattr(result, "pages") and result.pages:
            for i, page in enumerate(result.pages):
                page_text = page.get("text", "") if isinstance(page, dict) else str(page)
                pages.append(PageContent(page_number=i + 1, text=page_text))

        text = result.text if hasattr(result, "text") else str(result)
        markdown = result.markdown if hasattr(result, "markdown") else text

        return ParsedDocument(
            source=source,
            format=self._detect_format(source),
            text=text,
            markdown=markdown,
            metadata={
                "parser": "glm-ocr",
                "model": "GLM-OCR-0.9B",
            },
            pages=pages,
            raw=result,
        )

    async def aparse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Async variant - runs sync parse in a thread."""
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        """Parse multiple documents sequentially."""
        return [self.parse(source, **kwargs) for source in sources]

    @classmethod
    def is_available(cls) -> bool:
        """Check if glmocr is installed."""
        try:
            import glmocr  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Return supported format strings."""
        return ["pdf", "image", "docx", "html", "text", "markdown"]

    @staticmethod
    def _detect_format(source: str) -> DocumentFormat:
        """Detect document format from file extension."""
        suffix = Path(source).suffix.lower()
        return FORMAT_MAP.get(suffix, DocumentFormat.TEXT)
