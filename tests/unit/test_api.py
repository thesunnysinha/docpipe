from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


@patch("docpipe.server.app.psycopg2")
def test_delete_by_source_removes_chunks(mock_psycopg2, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_psycopg2.connect.return_value.__enter__ = lambda s: mock_conn
    mock_psycopg2.connect.return_value.__exit__ = MagicMock(return_value=False)

    resp = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docs",
            "source": "reports/q1.pdf",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["chunks_deleted"] == 3
    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args[0]
    assert "DELETE FROM" in call_args[0]
    assert "docs" in call_args[0]


@patch("docpipe.server.app.psycopg2")
def test_delete_table_not_found_returns_404(mock_psycopg2, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception('relation "nonexistent" does not exist')
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_psycopg2.connect.return_value.__enter__ = lambda s: mock_conn
    mock_psycopg2.connect.return_value.__exit__ = MagicMock(return_value=False)

    resp = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "nonexistent",
            "source": "doc.pdf",
        },
    )
    assert resp.status_code == 404
