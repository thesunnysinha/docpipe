"""Reusable conformance assertions for vector-store plugin authors."""

from __future__ import annotations

from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    VectorCapability,
    VectorQuery,
    VectorRecord,
    VectorStoreBinding,
    WriteBatch,
)


def assert_binding_shape(binding: VectorStoreBinding) -> None:
    """Raise ``AssertionError`` when advertised facets are unavailable."""
    if VectorCapability.DENSE_SEARCH in binding.capabilities:
        assert binding.reader is not None, "dense search requires a reader facet"
    if VectorCapability.UPSERT in binding.capabilities:
        assert binding.writer is not None, "upsert requires a writer facet"
    if VectorCapability.COLLECTION_ADMIN in binding.capabilities:
        assert binding.admin is not None, "collection administration requires an admin facet"
    if VectorCapability.HEALTH in binding.capabilities:
        assert binding.health is not None, "health capability requires a health facet"


async def assert_vector_store_conformance(
    binding: VectorStoreBinding,
    *,
    collection: CollectionRef,
    dimensions: int,
) -> None:
    """Exercise common create, write, search, delete, and health behavior."""
    assert_binding_shape(binding)
    assert binding.admin is not None
    assert binding.writer is not None
    assert binding.reader is not None
    await binding.admin.ensure_collection(collection, dimensions)
    record = VectorRecord(
        record_id="docpipe-conformance-record",
        text="Docpipe vector conformance record.",
        vector=tuple(0.5 for _ in range(dimensions)),
        source_id="docpipe-conformance-source",
    )
    result = await binding.writer.upsert(WriteBatch(collection, (record,)))
    assert result.requested == 1 and result.accepted == 1
    matches = await binding.reader.search(
        VectorQuery(collection, dense_vector=record.vector, limit=1)
    )
    assert matches and matches[0].record_id == record.record_id
    deleted = await binding.writer.delete_by_source(collection, record.source_id or "")
    assert deleted == 1
    if binding.health is not None:
        assert await binding.health.health()
