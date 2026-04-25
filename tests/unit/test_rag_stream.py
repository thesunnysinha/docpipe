"""Unit tests for POST /rag/stream SSE endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


VALID_REQUEST = {
    "question": "What is docpipe?",
    "connection_string": "postgresql://test/db",
    "table_name": "docs",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
}


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_rag_stream_returns_event_stream(client):
    """Endpoint returns 200 with text/event-stream content type and SSE tokens."""
    with (
        patch("docpipe.server.app.RAGPipeline") as mock_pipeline_cls,
        patch("docpipe.server.app.RAGConfig"),
    ):
        mock_pipeline = MagicMock()
        mock_pipeline.stream_query.return_value = iter(["Hello", " world", "!"])
        mock_pipeline_cls.return_value = mock_pipeline

        resp = client.post("/rag/stream", json=VALID_REQUEST)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "data: Hello\n\n" in resp.text
    assert "data: [DONE]\n\n" in resp.text


def test_rag_stream_all_tokens_present(client):
    """All tokens from stream_query appear in the SSE response body."""
    with (
        patch("docpipe.server.app.RAGPipeline") as mock_pipeline_cls,
        patch("docpipe.server.app.RAGConfig"),
    ):
        mock_pipeline = MagicMock()
        mock_pipeline.stream_query.return_value = iter(["Hello", " world", "!"])
        mock_pipeline_cls.return_value = mock_pipeline

        resp = client.post("/rag/stream", json=VALID_REQUEST)

    assert "Hello" in resp.text
    assert " world" in resp.text
    assert "!" in resp.text


def test_rag_stream_done_sentinel_at_end(client):
    """The [DONE] sentinel appears after all token data in the response body."""
    with (
        patch("docpipe.server.app.RAGPipeline") as mock_pipeline_cls,
        patch("docpipe.server.app.RAGConfig"),
    ):
        mock_pipeline = MagicMock()
        mock_pipeline.stream_query.return_value = iter(["Hello", " world", "!"])
        mock_pipeline_cls.return_value = mock_pipeline

        resp = client.post("/rag/stream", json=VALID_REQUEST)

    body = resp.text
    last_token_pos = body.rfind("data: !\n\n")
    done_pos = body.find("data: [DONE]\n\n")

    assert done_pos != -1, "[DONE] sentinel not found in response"
    assert last_token_pos != -1, "Last token not found in response"
    assert done_pos > last_token_pos, "[DONE] sentinel must appear after the last token"
