"""BaseExtractor protocol for structured data extraction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.core.types import ExtractionResult, ExtractionSchema


@runtime_checkable
class BaseExtractor(Protocol):
    """Protocol that all structured extractors must implement."""

    name: str

    def extract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: object,
    ) -> list[ExtractionResult]:
        """Extract structured data from text."""
        ...

    async def aextract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: object,
    ) -> list[ExtractionResult]:
        """Async variant of extract."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Return True if the underlying library is installed."""
        ...
