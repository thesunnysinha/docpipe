"""Minimal external Docpipe vector plugin using only public contracts."""

from __future__ import annotations

from collections import Counter

from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorCapability,
    VectorMatch,
    VectorQuery,
    VectorRecord,
    VectorStoreBinding,
    WriteBatch,
    WriteBatchResult,
)
from docpipe.plugins.loader import PluginFactoryContext


class MemoryVectorPlugin:
    """Small in-memory reference implementation; never use for durable data."""

    def __init__(self) -> None:
        self._collections: dict[str, dict[str, VectorRecord]] = {}
        self._dimensions: dict[str, int] = {}
        self.binding = VectorStoreBinding(
            capabilities=frozenset(
                {
                    VectorCapability.DENSE_SEARCH,
                    VectorCapability.UPSERT,
                    VectorCapability.DELETE_BY_SOURCE,
                    VectorCapability.COLLECTION_ADMIN,
                    VectorCapability.HEALTH,
                }
            ),
            reader=self,
            writer=self,
            admin=self,
            health=self,
        )

    async def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Create a collection or verify its existing vector width."""
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        previous = self._dimensions.setdefault(collection.name, dimensions)
        if previous != dimensions:
            raise ValueError("collection dimensions do not match")
        self._collections.setdefault(collection.name, {})

    async def delete_collection(self, collection: CollectionRef) -> None:
        """Remove one collection and all of its records."""
        self._collections.pop(collection.name, None)
        self._dimensions.pop(collection.name, None)

    async def upsert(self, batch: WriteBatch) -> WriteBatchResult:
        """Replace records by deterministic IDs."""
        records = self._collections[batch.collection.name]
        dimensions = self._dimensions[batch.collection.name]
        for record in batch.records:
            if len(record.vector) != dimensions:
                raise ValueError("record dimensions do not match")
            records[record.record_id] = record
        return WriteBatchResult(requested=len(batch.records), accepted=len(batch.records))

    async def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Score dense vectors with a dot product and stable tie breaking."""
        if query.dense_vector is None or query.filter is not None:
            raise ValueError("example supports unfiltered dense search only")
        records = self._collections.get(query.collection.name, {})
        scored = (
            (
                sum(
                    float(a) * float(b)
                    for a, b in zip(record.vector, query.dense_vector, strict=True)
                ),
                record,
            )
            for record in records.values()
        )
        ordered = sorted(scored, key=lambda item: (-item[0], item[1].record_id))
        return tuple(
            VectorMatch(
                record_id=record.record_id,
                score=score,
                text=record.text,
                metadata=record.metadata,
                source_id=record.source_id,
            )
            for score, record in ordered[: query.limit]
        )

    async def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Return source counts without claiming aggregation capability."""
        records = self._collections.get(collection.name, {}).values()
        counts = Counter(record.source_id for record in records if record.source_id)
        return tuple(
            SourceAggregate(source_id=source, record_count=count)
            for source, count in sorted(counts.items())
        )

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete exact source matches and report removed records."""
        records = self._collections.get(collection.name, {})
        identifiers = [key for key, record in records.items() if record.source_id == source_id]
        for key in identifiers:
            del records[key]
        return len(identifiers)

    async def health(self) -> bool:
        """The in-memory adapter is healthy while the instance exists."""
        return True


def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> MemoryVectorPlugin:
    """Validate the selected provider and return a fresh operation-local instance."""
    if config.provider != "example-memory":
        raise ValueError("wrong provider selected")
    return MemoryVectorPlugin()
