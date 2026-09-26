"""PaddleOCR PP-Structure document parser."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import PageContent, ParsedDocument
from docpipe.parsers.markitdown_parser import MarkItDownParser
from docpipe.parsers.url_safety import assert_safe_http_source


class PaddleOCRParser:
    """Parse documents with PaddleOCR PP-Structure.

    PaddleOCR is an optional backend. The engine is initialized lazily on the
    first parse call; advertised formats reflect this adapter's declaration,
    while actual support depends on the installed PaddleOCR build and runtime.
    Non-empty results are exposed as one aggregate page, and the upstream
    result is retained in ``ParsedDocument.raw``.
    """

    name = "paddleocr"
    license = "Apache-2.0"
    requires_gpu = False

    def __init__(self, **options: Any) -> None:
        """Validate optional dependency availability and save engine options.

        Raises:
            ParserNotInstalledError: If PaddleOCR is unavailable.
        """
        if not self.is_available():
            raise ParserNotInstalledError(
                "PaddleOCR is not installed. Install with: pip install docpipe-sdk[paddleocr]"
            )
        self._options = options
        self._engine: Any = None

    def _get_engine(self) -> Any:
        """Create and cache the PP-Structure engine on first use."""
        if self._engine is None:
            from paddleocr import PPStructureV3

            self._engine = PPStructureV3(**self._options)
        return self._engine

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Parse one local or approved HTTP(S) source with the cached engine.

        For mapping results, text is selected from ``markdown``, then
        ``text``, then a JSON serialization; other result types are stringified.
        Per-call options are passed to ``predict`` and the original result is
        retained as raw output.

        Raises:
            ParseError: If the upstream prediction raises an exception.
        """
        assert_safe_http_source(source)
        try:
            result = self._get_engine().predict(source, **kwargs)
        except Exception as e:
            raise ParseError(f"PaddleOCR failed on '{source}': {e}") from e
        if isinstance(result, dict):
            markdown = result.get("markdown") or result.get("text") or json.dumps(result)
        else:
            markdown = str(result)
        text = markdown
        pages = [PageContent(page_number=1, text=text)] if text.strip() else []
        return ParsedDocument(
            source=source,
            format=MarkItDownParser._detect_format(source),
            text=text,
            markdown=markdown,
            metadata={"parser": self.name},
            pages=pages,
            raw=result,
        )

    async def aparse(self, source: str, **kwargs: Any) -> ParsedDocument:
        """Run :meth:`parse` in a worker thread and return its result or error."""
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        """Parse sources sequentially; the first parse error stops the batch."""
        return [self.parse(s, **kwargs) for s in sources]

    @classmethod
    def is_available(cls) -> bool:
        """Return whether the top-level optional ``paddleocr`` package imports."""
        try:
            import paddleocr  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Return advertised format names; this does not probe engine support."""
        return ["pdf", "docx", "pptx", "xlsx", "image", "html"]
