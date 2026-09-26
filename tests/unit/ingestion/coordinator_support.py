"""Small deterministic ports for ingestion coordinator behavior specs."""

from __future__ import annotations

import asyncio

from docpipe.core.types import DocumentFormat, ParsedDocument
from docpipe.ingestion.document_builder import IngestionDocument
from docpipe.plugins.contracts.vectorstore import CollectionRef, WriteBatch, WriteBatchResult


class BuilderDouble:
    """Build a fixed number of source records."""

    def __init__(self, count: int) -> None:
        self.count = count

    def build(
        self, parsed: ParsedDocument, extractions: object = ()
    ) -> tuple[IngestionDocument, ...]:
        """Return stable records to observe batching."""
        return tuple(
            IngestionDocument(f"record-{index}", f"chunk-{index}", {"order": index}, parsed.source)
            for index in range(self.count)
        )


class ChunkerDouble:
    """Record chunking order and optionally block for cancellation."""

    def __init__(self, events: list[str], wait: asyncio.Event | None = None) -> None:
        self.events = events
        self.wait = wait
        self.started = asyncio.Event()

    async def split(
        self, documents: tuple[IngestionDocument, ...]
    ) -> tuple[IngestionDocument, ...]:
        """Record and return the supplied documents."""
        self.events.append("chunk")
        self.started.set()
        if self.wait is not None:
            await self.wait.wait()
        return documents


class EncoderDouble:
    """Return stable vector dimensions and record calls."""

    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def encode_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Encode one vector per text."""
        self.events.append(f"encode:{len(texts)}")
        return tuple((float(index + 1),) * 8 for index, _ in enumerate(texts))

    async def encode_query(self, text: str) -> tuple[float, ...]:
        """Return a fixed query vector."""
        return (0.0,) * 8


class AdminDouble:
    """Record collection creation with the inferred vector width."""

    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Record collection setup."""
        self.events.append(f"ensure:{dimensions}")

    async def delete_collection(self, collection: CollectionRef) -> None:
        """No-op collection deletion."""
        return None


class WriterDouble:
    """Record concurrent writes and simulate rejected or uncertain outcomes."""

    def __init__(self, events: list[str], *, rejected: int = 0, uncertain: int = 0) -> None:
        self.events = events
        self.rejected = rejected
        self.uncertain = uncertain
        self.batch_sizes: list[int] = []
        self.active = 0
        self.maximum_active = 0

    async def upsert(self, batch: WriteBatch) -> WriteBatchResult:
        """Record bounded concurrent batch writes."""
        self.events.append(f"write:{len(batch.records)}")
        self.batch_sizes.append(len(batch.records))
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return WriteBatchResult(
            requested=len(batch.records),
            accepted=len(batch.records) - self.rejected - self.uncertain,
            rejected=self.rejected,
            uncertain=self.uncertain,
        )

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Return no deletions for these ingestion-only specs."""
        return 0


def parsed_document() -> ParsedDocument:
    """Build one stable parser result."""
    return ParsedDocument(
        source="document.pdf", format=DocumentFormat.PDF, text="complete document"
    )
