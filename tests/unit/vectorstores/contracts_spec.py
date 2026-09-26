"""Tests for segregated structural vector-store facets."""

from __future__ import annotations

import pytest

from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    PluginHealthProbe,
    VectorCapability,
    VectorCollectionAdmin,
    VectorQuery,
    VectorReader,
    VectorStoreBinding,
    VectorWriter,
    WriteBatch,
    WriteBatchResult,
)


class ReaderDouble:
    async def search(self, query: VectorQuery):
        return ()

    async def aggregate_sources(self, collection: CollectionRef):
        return ()


class WriterDouble:
    async def upsert(self, batch: WriteBatch) -> WriteBatchResult:
        return WriteBatchResult(requested=len(batch.records), accepted=len(batch.records))

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        return 0


class AdminDouble:
    async def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        return None

    async def delete_collection(self, collection: CollectionRef) -> None:
        return None


class HealthDouble:
    async def health(self) -> bool:
        return True


def test_structural_doubles_satisfy_facets_without_inheritance() -> None:
    reader = ReaderDouble()
    writer = WriterDouble()
    admin = AdminDouble()
    health = HealthDouble()

    assert isinstance(reader, VectorReader)
    assert isinstance(writer, VectorWriter)
    assert isinstance(admin, VectorCollectionAdmin)
    assert isinstance(health, PluginHealthProbe)


def test_binding_requires_facets_for_advertised_capabilities() -> None:
    binding = VectorStoreBinding(
        capabilities=frozenset(
            {
                VectorCapability.DENSE_SEARCH,
                VectorCapability.UPSERT,
                VectorCapability.COLLECTION_ADMIN,
                VectorCapability.HEALTH,
            }
        ),
        reader=ReaderDouble(),
        writer=WriterDouble(),
        admin=AdminDouble(),
        health=HealthDouble(),
    )

    assert binding.reader is not None
    assert VectorCapability.DENSE_SEARCH.value.endswith(".v1")

    with pytest.raises(ValueError, match="reader facet"):
        VectorStoreBinding(capabilities=frozenset({VectorCapability.DENSE_SEARCH}))
