"""BaseParser protocol for document parsers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.core.types import ParsedDocument


@runtime_checkable
class BaseParser(Protocol):
    """Protocol that all document parsers must implement."""

    name: str

    def parse(self, source: str, **kwargs: object) -> ParsedDocument:
        """Parse a single document from a file path or URL."""
        ...

    async def aparse(self, source: str, **kwargs: object) -> ParsedDocument:
        """Async variant of parse."""
        ...

    def parse_batch(self, sources: list[str], **kwargs: object) -> list[ParsedDocument]:
        """Parse multiple documents."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Return True if the underlying library is installed."""
        ...

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Return list of supported format strings."""
        ...
