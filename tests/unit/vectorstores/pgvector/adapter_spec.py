"""Tests for the asynchronous pgvector contract adapter."""

from __future__ import annotations

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorCapability,
    VectorMatch,
    VectorQuery,
    VectorRecord,
    WriteBatch,
)
from docpipe.plugins.credentials import EnvironmentCredentialResolver
from docpipe.plugins.errors import VectorStoreConnectionError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.vectorstores.pgvector.adapter import PgVectorAdapter
from docpipe.vectorstores.pgvector.configuration import PgVectorConfig
from docpipe.vectorstores.pgvector.factory import create_plugin


class RepositoryDouble:
    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}

    def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        self.dimensions = dimensions

    def delete_collection(self, collection: CollectionRef) -> None:
        self.records.clear()

    def upsert(self, batch: WriteBatch) -> int:
        self.records.update({record.record_id: record for record in batch.records})
        return len(batch.records)

    def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        return tuple(
            VectorMatch(item.record_id, 1.0, item.text, item.metadata, item.source_id)
            for item in self.records.values()
        )

    def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        matching = [key for key, item in self.records.items() if item.source_id == source_id]
        for key in matching:
            self.records.pop(key)
        return len(matching)

    def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        return (SourceAggregate("source.pdf", len(self.records)),)

    def health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_adapter_exposes_complete_binding_and_deterministic_operations() -> None:
    repository = RepositoryDouble()
    async with BoundedBlockingRunner(max_concurrency=1) as runner:
        adapter = PgVectorAdapter(PgVectorConfig(dsn="postgresql://db/docpipe"), repository, runner)
        collection = CollectionRef("documents")
        await adapter.ensure_collection(collection, 2)
        result = await adapter.upsert(
            WriteBatch(
                collection,
                (VectorRecord("one", "text", [0.1, 0.2], source_id="source.pdf"),),
            )
        )
        matches = await adapter.search(VectorQuery(collection, dense_vector=[0.1, 0.2]))

        assert result.accepted == 1
        assert matches[0].record_id == "one"
        assert await adapter.delete_by_source(collection, "source.pdf") == 1
        assert await adapter.health()
        assert VectorCapability.METADATA_FILTER in adapter.binding.capabilities


@pytest.mark.asyncio
async def test_adapter_translates_connection_failure_without_dsn() -> None:
    class BrokenRepository(RepositoryDouble):
        def health(self) -> bool:
            raise OSError("postgresql://admin:secret@db/docpipe")

    config = PgVectorConfig(dsn="postgresql://admin:secret@db/docpipe")
    async with BoundedBlockingRunner(max_concurrency=1) as runner:
        adapter = PgVectorAdapter(config, BrokenRepository(), runner)
        with pytest.raises(VectorStoreConnectionError) as caught:
            await adapter.health()

    assert "secret" not in str(caught.value.to_dict())
    assert isinstance(caught.value.__cause__, OSError)


@pytest.mark.asyncio
async def test_write_connection_failure_uses_connection_error_classification() -> None:
    class BrokenRepository(RepositoryDouble):
        def upsert(self, batch: WriteBatch) -> int:
            raise ConnectionError("database unavailable")

    async with BoundedBlockingRunner(max_concurrency=1) as runner:
        adapter = PgVectorAdapter(
            PgVectorConfig(dsn="postgresql://db/docpipe"),
            BrokenRepository(),
            runner,
        )
        batch = WriteBatch(
            CollectionRef("documents"),
            (VectorRecord("one", "text", [0.1]),),
        )
        with pytest.raises(VectorStoreConnectionError):
            await adapter.upsert(batch)


@pytest.mark.asyncio
async def test_factory_resolves_dsn_reference_and_injects_blocking_runner() -> None:
    config = PluginConfig(
        provider="pgvector",
        options={
            "dsn_secret": {"kind": "environment", "name": "PGVECTOR_DSN"},
            "collection": "documents",
        },
    )
    resolver = EnvironmentCredentialResolver({"PGVECTOR_DSN": "postgresql://db/docpipe"})
    async with BoundedBlockingRunner(max_concurrency=1) as runner:
        adapter = create_plugin(
            config,
            context=PluginFactoryContext(blocking_runner=runner, credentials=resolver),
        )

    assert isinstance(adapter, PgVectorAdapter)
