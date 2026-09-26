"""Unit tests for POST /cost/estimate."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_cost_estimate_balanced_ten_pages(client):
    resp = client.post(
        "/cost/estimate",
        json={"preset": "balanced", "page_count": 10, "embedding_provider": "openai"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["preset"] == "balanced"
    assert body["page_count"] == 10
    assert body["estimated_parse_seconds"] == 12.0
    assert body["estimated_chunks"] == 30
    assert body["estimated_embedding_usd"] > 0


def test_cost_estimate_rejects_invalid_page_count(client):
    resp = client.post(
        "/cost/estimate",
        json={"preset": "fast", "page_count": 0},
    )
    assert resp.status_code == 422
