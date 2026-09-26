"""Mutation vector-store facet."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.plugins.contracts.vectorstore.models import (
    CollectionRef,
    WriteBatch,
    WriteBatchResult,
)


@runtime_checkable
class VectorWriter(Protocol):
    """Write records and delete records by normalized source."""

    async def upsert(self, batch: WriteBatch) -> WriteBatchResult:
        """Insert or replace a deterministic batch of records."""
        ...

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete exact source matches and return the removed count."""
        ...
