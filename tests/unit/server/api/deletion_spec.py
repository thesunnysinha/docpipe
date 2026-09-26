"""Legacy deletion endpoints preserve counts, errors, and safe SQL names."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg2.errors


@patch("psycopg2.connect")
def should_return_deleted_chunk_count(mock_connect, client) -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 3
    connection.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value.__enter__.return_value = connection

    response = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docs",
            "source": "reports/q1.pdf",
        },
    )
    assert response.status_code == 200
    assert response.json()["chunks_deleted"] == 3
    cursor.execute.assert_called_once()
    statement = cursor.execute.call_args[0][0]
    assert "DELETE FROM" in statement and "docs" in statement


@patch("psycopg2.connect")
def should_return_404_for_missing_collection(mock_connect, client) -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.execute.side_effect = psycopg2.errors.UndefinedTable(
        'relation "nonexistent" does not exist'
    )
    connection.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value.__enter__.return_value = connection

    response = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "nonexistent",
            "source": "doc.pdf",
        },
    )
    assert response.status_code == 404


@patch("docpipe.server.routers.ingest.psycopg2")
def should_reject_invalid_collection_name(mock_psycopg2, client) -> None:
    response = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docs; DROP TABLE langchain_pg_embedding; --",
            "source": "doc.pdf",
        },
    )
    assert response.status_code == 422


@patch("psycopg2.connect")
def should_preserve_legacy_contains_mode(mock_connect, client) -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 2
    connection.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value.__enter__.return_value = connection

    response = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docs",
            "match_mode": "contains",
            "source_contains": "reports/",
        },
    )
    assert response.status_code == 200
    assert response.json()["chunks_deleted"] == 2
    assert "LIKE" in cursor.execute.call_args[0][0]
