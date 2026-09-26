"""Optional contextual enrichment behind a narrow text-generation port."""

from __future__ import annotations

import logging
from typing import Protocol

from docpipe.ingestion.document_builder import IngestionDocument

_LOGGER = logging.getLogger(__name__)


class ContextGenerator(Protocol):
    """Generate short context for one chunk without exposing an LLM type."""

    async def generate(self, full_text: str, chunk_text: str) -> str:
        """Return context text for a chunk."""
        ...


class Contextualizer(Protocol):
    """Transform immutable ingestion documents with optional context."""

    async def apply(
        self,
        documents: tuple[IngestionDocument, ...],
        full_text: str,
    ) -> tuple[IngestionDocument, ...]:
        """Return enriched documents in input order."""
        ...


class ContextualInjector:
    """Prepend generated context while failing open per chunk for compatibility."""

    def __init__(
        self,
        generator: ContextGenerator,
        *,
        max_document_characters: int = 4_000,
        logger: logging.Logger | None = None,
    ) -> None:
        if max_document_characters < 1:
            raise ValueError("max_document_characters must be at least one")
        self._generator = generator
        self._max_document_characters = max_document_characters
        self._logger = logger or _LOGGER

    async def apply(
        self,
        documents: tuple[IngestionDocument, ...],
        full_text: str,
    ) -> tuple[IngestionDocument, ...]:
        """Enrich each chunk, preserving it unchanged if generation fails."""
        bounded_text = full_text[: self._max_document_characters]
        enriched: list[IngestionDocument] = []
        for document in documents:
            try:
                context = (await self._generator.generate(bounded_text, document.text)).strip()
            except Exception:  # noqa: BLE001 -- compatibility mode intentionally fails open.
                self._logger.warning(
                    "ingestion.contextualization.skipped",
                    extra={
                        "event": "ingestion.contextualization.skipped",
                        "error_code": "context_generation_failed",
                    },
                )
                enriched.append(document)
                continue
            enriched.append(
                document.with_text(f"{context}\n\n{document.text}") if context else document
            )
        return tuple(enriched)
