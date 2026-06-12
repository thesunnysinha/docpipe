"""MinerU adapter for high-accuracy document parsing."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from docpipe.core.errors import ParseError, ParserNotInstalledError
from docpipe.core.types import PageContent, ParsedDocument
from docpipe.parsers.markitdown_parser import MarkItDownParser


class MinerUParser:
    """Document parser using OpenDataLab MinerU."""

    name = "mineru"
    license = "Apache-2.0"
    requires_gpu = True

    def __init__(self, **options: Any) -> None:
        if not self.is_available():
            raise ParserNotInstalledError(
                "MinerU is not installed. Install with: pip install docpipe-sdk[mineru]"
            )
        self._options = options

    def parse(self, source: str, **kwargs: Any) -> ParsedDocument:
        try:
            from mineru.cli.common import do_parse
        except ImportError as e:
            raise ParserNotInstalledError("mineru package not installed") from e

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            try:
                do_parse(
                    path_list=[source],
                    output_dir=str(out_dir),
                    **{**self._options, **kwargs},
                )
            except Exception as e:
                raise ParseError(f"MinerU failed on '{source}': {e}") from e
            md_files = list(out_dir.rglob("*.md"))
            if not md_files:
                raise ParseError(f"MinerU produced no markdown for '{source}'")
            markdown = md_files[0].read_text(encoding="utf-8")
        text = markdown
        pages = [PageContent(page_number=1, text=text)] if text.strip() else []
        return ParsedDocument(
            source=source,
            format=MarkItDownParser._detect_format(source),
            text=text,
            markdown=markdown,
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
            import mineru  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def supported_formats(cls) -> list[str]:
        return ["pdf", "docx", "pptx", "xlsx", "image"]
