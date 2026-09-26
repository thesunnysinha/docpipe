"""Read-only vector-store facet."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.plugins.contracts.vectorstore.models import (
    CollectionRef,
    SourceAggregate,
    VectorMatch,
    VectorQuery,
)


@runtime_checkable
class VectorReader(Protocol):
    """Search and aggregate stored vectors without mutation."""

    async def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Return deterministic scored matches for a query."""
        ...

    async def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Return stored record counts grouped by source."""
        ...
