"""Tests for metadata filtering support in RAG query, stream, and search endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


VALID_RAG_REQUEST = {
    "question": "test",
    "connection_string": "postgresql://test/db",
    "table_name": "docs",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
    "system_prompt": "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
    "hyde_prompt": "Hypothetical passage for: {question}",
    "multi_query_prompt": "Generate {n} variants of: {question}",
    "auto_strategy_prompt": "Reply naive for: {question}",
}

VALID_SEARCH_REQUEST = {
    "query": "test",
    "connection_string": "postgresql://test/db",
    "table_name": "docs",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
}


def _make_fake_result():
    result = MagicMock()
    result.query = "test"
    result.answer = "fake answer"
    result.strategy = "naive"
    result.chunks = []
    result.sources = []
    result.timing_seconds = 0.1
    return result


def test_rag_query_passes_filters_to_rag_config(client):
    """Filters sent in the request body should be forwarded to RAGConfig."""
    with (
        patch("docpipe.server.request_mapping.RAGConfig") as MockConfig,
        patch("docpipe.server.services.rag.RAGPipeline") as MockPipeline,
    ):
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        async def fake_aquery(question):
            return _make_fake_result()

        mock_pipeline.aquery = fake_aquery

        # RAGConfig returns a MagicMock so RAGPipeline(config) works fine
        MockConfig.return_value = MagicMock()

        resp = client.post(
            "/rag/query",
            json={**VALID_RAG_REQUEST, "filters": {"source": "doc.pdf"}},
        )

        assert resp.status_code == 200
        filters_passed = MockConfig.call_args.kwargs.get("filters")
        assert filters_passed == {"source": "doc.pdf"}


def test_rag_query_default_filters_is_empty_dict(client):
    """When no filters key is sent, RAGConfig should receive an empty dict."""
    with (
        patch("docpipe.server.request_mapping.RAGConfig") as MockConfig,
        patch("docpipe.server.services.rag.RAGPipeline") as MockPipeline,
    ):
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        async def fake_aquery(question):
            return _make_fake_result()

        mock_pipeline.aquery = fake_aquery
        MockConfig.return_value = MagicMock()

        resp = client.post("/rag/query", json=VALID_RAG_REQUEST)

        assert resp.status_code == 200
        filters_passed = MockConfig.call_args.kwargs.get("filters")
        assert filters_passed == {}


def test_search_passes_filters_to_selected_reader(client):
    """Filters sent in the /search request reach the selected search coordinator."""
    with (
        patch("docpipe.server.services.ingest.IngestionPipeline") as MockIngestion,
        patch(
            "docpipe.server.services.ingest.build_search_coordinator",
            new_callable=AsyncMock,
        ) as build_search,
    ):
        selected = MagicMock()
        selected.search = AsyncMock(return_value=())
        build_search.return_value = selected
        MockIngestion._create_embeddings.return_value = object()

        resp = client.post(
            "/search",
            json={**VALID_SEARCH_REQUEST, "filters": {"type": "report"}},
        )

        assert resp.status_code == 200
        assert selected.search.call_args.kwargs["filters"] == {"type": "report"}


def test_rag_config_accepts_filters_field():
    """RAGConfig should have a filters field with a default of empty dict."""
    from docpipe.core.types import RAGConfig

    # Explicit filters
    config = RAGConfig(
        connection_string="postgresql://x/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        filters={"key": "val"},
    )
    assert config.filters == {"key": "val"}

    # Default filters
    config_default = RAGConfig(
        connection_string="postgresql://x/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )
    assert config_default.filters == {}


def test_search_default_filters_passes_none_after_guard(client):
    with (
        patch("docpipe.server.services.ingest.IngestionPipeline") as MockIngestion,
        patch(
            "docpipe.server.services.ingest.build_search_coordinator",
            new_callable=AsyncMock,
        ) as build_search,
    ):
        selected = MagicMock()
        selected.search = AsyncMock(return_value=())
        build_search.return_value = selected
        MockIngestion._create_embeddings.return_value = object()

        resp = client.post("/search", json=VALID_SEARCH_REQUEST)  # no filters key

        assert resp.status_code == 200
        assert selected.search.call_args.kwargs["filters"] == {}
