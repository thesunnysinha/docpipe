"""Tests for metadata filtering support in RAG query, stream, and search endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


VALID_RAG_REQUEST = {
    "question": "test",
    "connection_string": "postgresql://test/db",
    "table_name": "docs",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
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
        patch("docpipe.server.app.RAGConfig") as MockConfig,
        patch("docpipe.server.app.RAGPipeline") as MockPipeline,
    ):
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        import asyncio

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
        patch("docpipe.server.app.RAGConfig") as MockConfig,
        patch("docpipe.server.app.RAGPipeline") as MockPipeline,
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


def test_search_passes_filters_to_ingestion_pipeline(client):
    """Filters sent in the /search request should be forwarded to IngestionPipeline.search()."""
    with patch("docpipe.ingestion.pipeline.IngestionPipeline") as MockIngestion:
        mock_pipeline = MagicMock()
        MockIngestion.return_value = mock_pipeline
        mock_pipeline.search.return_value = []

        resp = client.post(
            "/search",
            json={**VALID_SEARCH_REQUEST, "filters": {"type": "report"}},
        )

        assert resp.status_code == 200
        call_args = mock_pipeline.search.call_args
        # Check keyword args first, then fall back to positional
        filters_passed = call_args.kwargs.get("filters")
        if filters_passed is None and len(call_args.args) >= 3:
            filters_passed = call_args.args[2]
        assert filters_passed == {"type": "report"}


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
