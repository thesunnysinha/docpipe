"""PaddleOCR PP-Structure document parser."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import PageContent, ParsedDocument
from docpipe.parsers.markitdown_parser import MarkItDownParser


class PaddleOCRParser:
    """Document parser using PaddleOCR PP-Structure."""

    name = "paddleocr"
    license = "Apache-2.0"
    requires_gpu = False

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ParserNotInstalledError(
                "PaddleOCR is not installed. Install with: pip install docpipe-sdk[paddleocr]"
            )
        self._options = options
        self._engine: Any = None

    def _get_engine(self) -> Any:
        if self._engine is None:
            from paddleocr import PPStructureV3

            self._engine = PPStructureV3(**self._options)
        return self._engine

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
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
        return await asyncio.to_thread(self.parse, source, **kwargs)

    def parse_batch(self, sources: list[str], **kwargs: Any) -> list[ParsedDocument]:
        return [self.parse(s, **kwargs) for s in sources]

    @classmethod
    def is_available(cls) -> bool:
        try:
            import paddleocr  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        return ["pdf", "docx", "pptx", "xlsx", "image", "html"]
