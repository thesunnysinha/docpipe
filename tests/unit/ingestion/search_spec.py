"""Search follows the selected plugin's reader facet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.ingestion.search import SearchCoordinator
from docpipe.plugins.contracts.vectorstore import (
    And,
    CollectionRef,
    Equals,
    VectorCapability,
    VectorMatch,
    VectorQuery,
)
from docpipe.plugins.errors import PluginCapabilityError
from docpipe.registry.registry import PluginRegistry
from docpipe.schemas.search import SearchRequest
from docpipe.server.services.ingest import IngestService


@dataclass
class Encoder:
    async def encode_query(self, text: str) -> tuple[float, ...]:
        assert text == "find this"
        return (0.1, 0.2)


class Reader:
    def __init__(self) -> None:
        self.query: VectorQuery | None = None

    async def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        self.query = query
        return (VectorMatch(record_id="a", score=0.9, text="result", metadata={"page": 2}),)


@pytest.mark.asyncio
async def test_search_uses_selected_reader_with_typed_filters() -> None:
    reader = Reader()
    search = SearchCoordinator(
        reader=reader,
        encoder=Encoder(),
        collection=CollectionRef("docs"),
        capabilities=frozenset({VectorCapability.DENSE_SEARCH, VectorCapability.METADATA_FILTER}),
    )

    matches = await search.search("find this", limit=5, filters={"page": 2, "type": "report"})

    assert matches[0].text == "result"
    assert reader.query is not None
    assert reader.query.collection == CollectionRef("docs")
    assert reader.query.limit == 5
    assert reader.query.dense_vector == (0.1, 0.2)
    assert reader.query.filter == And((Equals("page", 2), Equals("type", "report")))


@pytest.mark.asyncio
async def test_search_rejects_missing_capability_before_embedding() -> None:
    search = SearchCoordinator(
        reader=Reader(),
        encoder=Encoder(),
        collection=CollectionRef("docs"),
        capabilities=frozenset({VectorCapability.DENSE_SEARCH}),
    )

    with pytest.raises(PluginCapabilityError, match="metadata filtering"):
        await search.search("find this", filters={"page": 2})


@pytest.mark.asyncio
async def test_search_rejects_unsafe_filter_field() -> None:
    search = SearchCoordinator(
        reader=Reader(),
        encoder=Encoder(),
        collection=CollectionRef("docs"),
        capabilities=frozenset({VectorCapability.DENSE_SEARCH, VectorCapability.METADATA_FILTER}),
    )

    with pytest.raises(ConfigurationError, match="filters"):
        await search.search("find this", filters={"page; DROP TABLE": 2})


@pytest.mark.asyncio
async def test_search_service_uses_selected_provider_without_legacy_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected: dict[str, Any] = {}

    async def build_selected(config: Any, **kwargs: Any) -> SearchCoordinator:
        selected["provider"] = config.vector_store.provider
        selected["runtime"] = kwargs["runtime"].is_active
        return SearchCoordinator(
            reader=Reader(),
            encoder=Encoder(),
            collection=CollectionRef("docs"),
            capabilities=frozenset({VectorCapability.DENSE_SEARCH}),
        )

    monkeypatch.setattr("docpipe.server.services.ingest.build_search_coordinator", build_selected)
    monkeypatch.setattr(
        "docpipe.server.services.ingest.IngestionPipeline._create_embeddings",
        lambda config: object(),
    )
    settings = DocpipeSettings()
    runtime = build_runtime(settings)
    request = SearchRequest(
        query="find this",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="test",
        vector_store=VectorStoreOptions(provider="qdrant", options={"collection": "docs"}),
    )

    async with runtime:
        response = await IngestService(settings, PluginRegistry(), runtime).search(request)

    assert selected == {"provider": "qdrant", "runtime": True}
    assert response.results[0].content == "result"
    assert response.results[0].score == 0.9
