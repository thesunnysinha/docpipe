"""Health endpoint dependency checks."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from docpipe.config.settings import DocpipeSettings
from docpipe.server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_health_includes_dependencies(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "dependencies" in body
    assert body["status"] == "ok"


@patch("docpipe.server.health.psycopg2.connect")
def test_health_db_failure_marks_unavailable(mock_connect, client):
    mock_connect.side_effect = RuntimeError("secret-password connection refused")
    client.app.state.docpipe_runtime.settings = DocpipeSettings(
        health_check_db=True,
        db_connection_string="postgresql://bad:secret-password@db/test",
        health_check_embedding=False,
    )
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unavailable"
    assert any(
        d["name"] == "database" and d["status"] == "unavailable" for d in body["dependencies"]
    )
    assert "secret-password" not in resp.text
