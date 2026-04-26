from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg2.errors
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
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_psycopg2.connect.return_value.__enter__.return_value = mock_conn

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
    mock_cursor.execute.side_effect = psycopg2.errors.UndefinedTable('relation "nonexistent" does not exist')
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_psycopg2.connect.return_value.__enter__.return_value = mock_conn
    mock_psycopg2.errors.UndefinedTable = psycopg2.errors.UndefinedTable

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


@patch("docpipe.server.app.psycopg2")
def test_delete_invalid_table_name_returns_422(mock_psycopg2, client):
    resp = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docs; DROP TABLE langchain_pg_embedding; --",
            "source": "doc.pdf",
        },
    )
    assert resp.status_code == 422


def test_rag_query_passes_api_key_to_llm(client):
    """api_key in request body must reach LLM instantiation."""
    with patch("docpipe.rag.pipeline.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="answer")
        mock_create_llm.return_value = mock_llm

        with patch("docpipe.rag.pipeline.RAGPipeline._create_embeddings") as mock_emb, \
             patch("docpipe.rag.pipeline.RAGPipeline._get_vectorstore") as mock_vs:
            mock_emb.return_value = MagicMock()
            mock_vs.return_value = MagicMock(
                similarity_search_with_score=MagicMock(return_value=[])
            )
            resp = client.post("/rag/query", json={
                "question": "What is X?",
                "connection_string": "postgresql://test/db",
                "table_name": "docs",
                "embedding_provider": "openai",
                "embedding_model": "text-embedding-3-small",
                "llm_provider": "openai",
                "llm_model": "gpt-4o-mini",
                "api_key": "sk-test-key",
            })
        mock_create_llm.assert_called_with("openai", "gpt-4o-mini", "sk-test-key")


def test_generate_returns_content(client):
    """POST /generate calls the LLM and returns the text response."""
    with patch("docpipe.rag.pipeline.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Photosynthesis Overview")
        mock_create_llm.return_value = mock_llm

        resp = client.post("/generate", json={
            "prompt": "Generate a 3-5 word title for: photosynthesis",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
        })
    assert resp.status_code == 200
    assert resp.json()["content"] == "Photosynthesis Overview"
    mock_create_llm.assert_called_with("openai", "gpt-4o-mini", None)


def test_generate_with_api_key(client):
    """api_key in request is forwarded to create_llm."""
    with patch("docpipe.rag.pipeline.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Result")
        mock_create_llm.return_value = mock_llm

        client.post("/generate", json={
            "prompt": "hello",
            "llm_provider": "anthropic",
            "llm_model": "claude-3-5-haiku-latest",
            "api_key": "sk-ant-test",
        })
    mock_create_llm.assert_called_with("anthropic", "claude-3-5-haiku-latest", "sk-ant-test")


def test_generate_unknown_provider_returns_400(client):
    """Unknown llm_provider returns HTTP 400."""
    resp = client.post("/generate", json={
        "prompt": "hello",
        "llm_provider": "nonexistent",
        "llm_model": "some-model",
    })
    assert resp.status_code == 400
