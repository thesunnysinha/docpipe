"""Tests for TurboVec vector facets and write serialization."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorCapability,
    VectorMatch,
    VectorQuery,
    VectorRecord,
    WriteBatch,
)
from docpipe.vectorstores.turbovec.adapter import TurboVecAdapter
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig


class RepositoryDouble:
    def __init__(self) -> None:
        self.active_writes = 0
        self.maximum_writes = 0
        self.lock = threading.Lock()
        self.records: dict[str, VectorRecord] = {}

    def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        return None

    def delete_collection(self, collection: CollectionRef) -> None:
        self.records.clear()

    def upsert(self, batch: WriteBatch) -> int:
        with self.lock:
            self.active_writes += 1
            self.maximum_writes = max(self.maximum_writes, self.active_writes)
        time.sleep(0.01)
        self.records.update({record.record_id: record for record in batch.records})
        with self.lock:
            self.active_writes -= 1
        return len(batch.records)

    def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        return tuple(
            VectorMatch(item.record_id, 1.0, item.text, item.metadata, item.source_id)
            for item in self.records.values()
        )

    def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        keys = [key for key, value in self.records.items() if value.source_id == source_id]
        for key in keys:
            self.records.pop(key)
        return len(keys)

    def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        counts: dict[str, int] = {}
        for record in self.records.values():
            if record.source_id:
                counts[record.source_id] = counts.get(record.source_id, 0) + 1
        return tuple(SourceAggregate(key, value) for key, value in sorted(counts.items()))

    def health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_adapter_exposes_only_supported_capabilities_and_serializes_writes(
    tmp_path,
) -> None:
    repository = RepositoryDouble()
    batch = WriteBatch(
        CollectionRef("documents"),
        (VectorRecord("one", "text", [0.1] * 8, source_id="source.pdf"),),
    )
    async with BoundedBlockingRunner(max_concurrency=4) as runner:
        adapter = TurboVecAdapter(TurboVecConfig(index_root=tmp_path), repository, runner)
        await asyncio.gather(*(adapter.upsert(batch) for _ in range(4)))

        assert repository.maximum_writes == 1
        assert VectorCapability.DENSE_SEARCH in adapter.binding.capabilities
        assert VectorCapability.SPARSE_SEARCH not in adapter.binding.capabilities
        assert VectorCapability.HYBRID_SEARCH not in adapter.binding.capabilities
        assert await adapter.delete_by_source(batch.collection, "source.pdf") == 1
