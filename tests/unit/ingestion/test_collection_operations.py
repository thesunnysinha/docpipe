"""Delete and source-list requests can use any selected vector plugin."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorCapability,
    VectorStoreBinding,
)
from docpipe.registry.registry import PluginRegistry
from docpipe.schemas.delete import DeleteRequest
from docpipe.schemas.sources import ListSourcesRequest
from docpipe.server.services.ingest import IngestService


class FakeStore:
    def __init__(self) -> None:
        self.deleted: tuple[str, str] | None = None

    @property
    def binding(self) -> VectorStoreBinding:
        return VectorStoreBinding(
            capabilities=frozenset(
                {VectorCapability.DELETE_BY_SOURCE, VectorCapability.SOURCE_AGGREGATION}
            ),
            reader=self,
            writer=self,
        )

    async def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        self.deleted = (collection.name, source_id)
        return 2

    async def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        assert collection.name == "docs"
        return (SourceAggregate(source_id="s3://bucket/report.pdf", record_count=2),)


class Loaded:
    def __init__(self, store: FakeStore) -> None:
        self.store = store

    def create(self, config: Any, *, context: Any) -> FakeStore:
        assert config.provider == "qdrant"
        assert config.options["collection"] == "docs"
        return self.store


@pytest.mark.asyncio
async def test_new_provider_delete_and_list_use_facets_without_legacy_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = DocpipeSettings()
    runtime = build_runtime(settings)
    store = FakeStore()
    loaded: list[str] = []

    def load(category: Any, name: str) -> Loaded:
        loaded.append(name)
        return Loaded(store)

    monkeypatch.setattr(runtime, "load_plugin", load)
    service = IngestService(settings, PluginRegistry(), runtime)
    envelope = VectorStoreOptions(provider="qdrant", options={"collection": "docs"})
    deletion = DeleteRequest(
        table_name="docs", source="s3://bucket/report.pdf", vector_store=envelope
    )
    listing = ListSourcesRequest(table_name="docs", vector_store=envelope)

    async with runtime:
        deleted = await service.delete(deletion)
        listed = await service.list_sources(listing)

    assert deleted.chunks_deleted == 2
    assert store.deleted == ("docs", "s3://bucket/report.pdf")
    assert listed.total_chunks == 2
    assert listed.sources[0].source == "s3://bucket/report.pdf"
    assert loaded == ["qdrant", "qdrant"]


def test_new_provider_rejects_unsupported_contains_and_filtered_aggregation() -> None:
    selected = VectorStoreOptions(provider="qdrant", options={"collection": "docs"})
    deletion = DeleteRequest(
        table_name="docs",
        source_contains="report",
        match_mode="contains",
        vector_store=selected,
    )
    listing = ListSourcesRequest(
        table_name="docs", vector_store=selected, filters={"type": "report"}
    )

    from docpipe.ingestion.collection_operations import validate_plugin_delete, validate_plugin_list

    with pytest.raises(ConfigurationError, match="exact"):
        validate_plugin_delete(deletion)
    with pytest.raises(ConfigurationError, match="filters"):
        validate_plugin_list(listing)


def test_legacy_collection_requests_still_require_connection_string() -> None:
    with pytest.raises(ValidationError, match="connection_string"):
        DeleteRequest(table_name="docs", source="report.pdf")
    with pytest.raises(ValidationError, match="connection_string"):
        ListSourcesRequest(table_name="docs")
