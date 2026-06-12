"""Unit tests for POST /ingest/stream SSE endpoint."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app

VALID_REQUEST = {
    "source": "/tmp/sample.pdf",
    "connection_string": "postgresql://test/db",
    "table_name": "docs",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "preset": "balanced",
}


@pytest.fixture()
def client():
    return TestClient(create_app())


async def _fake_ingest_stream(self, _req):
    yield 'event: progress\ndata: {"stage": "resolve", "percent": 5}\n\n'
    yield 'event: progress\ndata: {"stage": "complete", "percent": 100}\n\n'
    yield "data: [DONE]\n\n"


@patch("docpipe.server.services.ingest.IngestService.stream", _fake_ingest_stream)
def test_ingest_stream_returns_event_stream(client):
    resp = client.post("/ingest/stream", json=VALID_REQUEST)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "event: progress" in resp.text
    assert '"stage": "complete"' in resp.text
    assert "data: [DONE]\n\n" in resp.text


@patch(
    "docpipe.server.services.ingest.IngestService._resolve_and_parse",
    side_effect=RuntimeError("ingest failed"),
)
def test_ingest_stream_error_yields_error_event(_mock_resolve, client):
    resp = client.post("/ingest/stream", json=VALID_REQUEST)

    assert resp.status_code == 200
    assert "event: error" in resp.text
    assert "ingest failed" in resp.text
