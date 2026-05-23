from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg2.errors
import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


@patch("psycopg2.connect")
def test_delete_by_source_removes_chunks(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

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


@patch("psycopg2.connect")
def test_delete_table_not_found_returns_404(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    err = psycopg2.errors.UndefinedTable('relation "nonexistent" does not exist')
    mock_cursor.execute.side_effect = err
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

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

        with (
            patch("docpipe.rag.pipeline.RAGPipeline._create_embeddings") as mock_emb,
            patch("docpipe.rag.pipeline.RAGPipeline._get_vectorstore") as mock_vs,
        ):
            mock_emb.return_value = MagicMock()
            mock_vs.return_value = MagicMock(
                similarity_search_with_score=MagicMock(return_value=[])
            )
            client.post(
                "/rag/query",
                json={
                    "question": "What is X?",
                    "connection_string": "postgresql://test/db",
                    "table_name": "docs",
                    "embedding_provider": "openai",
                    "embedding_model": "text-embedding-3-small",
                    "llm_provider": "openai",
                    "llm_model": "gpt-4o-mini",
                    "api_key": "sk-test-key",
                    "system_prompt": "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
                    "hyde_prompt": "Hypothetical passage for: {question}",
                    "multi_query_prompt": "Generate {n} variants of: {question}",
                    "auto_strategy_prompt": "Reply naive for: {question}",
                },
            )
        mock_create_llm.assert_called_with("openai", "gpt-4o-mini", "sk-test-key")


def test_generate_returns_content(client):
    """POST /generate calls the LLM and returns the text response."""
    with patch("docpipe.rag.pipeline.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Photosynthesis Overview")
        mock_create_llm.return_value = mock_llm

        resp = client.post(
            "/generate",
            json={
                "prompt": "Generate a 3-5 word title for: photosynthesis",
                "llm_provider": "openai",
                "llm_model": "gpt-4o-mini",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Photosynthesis Overview"
    mock_create_llm.assert_called_with("openai", "gpt-4o-mini", None)


def test_generate_with_api_key(client):
    """api_key in request is forwarded to create_llm."""
    with patch("docpipe.rag.pipeline.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Result")
        mock_create_llm.return_value = mock_llm

        resp = client.post(
            "/generate",
            json={
                "prompt": "hello",
                "llm_provider": "anthropic",
                "llm_model": "claude-3-5-haiku-latest",
                "api_key": "sk-ant-test",
            },
        )
    assert resp.status_code == 200
    mock_create_llm.assert_called_with("anthropic", "claude-3-5-haiku-latest", "sk-ant-test")


def test_generate_unknown_provider_returns_400(client):
    """Unknown llm_provider returns HTTP 400."""
    resp = client.post(
        "/generate",
        json={
            "prompt": "hello",
            "llm_provider": "nonexistent",
            "llm_model": "some-model",
        },
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error_type"] == "configuration"


def test_health_returns_dependencies(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "dependencies" in resp.json()


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "docpipe" in resp.text or "python_info" in resp.text


@patch("psycopg2.connect")
def test_delete_source_contains(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 2
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

    resp = client.request(
        "DELETE",
        "/ingest",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docs",
            "match_mode": "contains",
            "source_contains": "reports/",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["chunks_deleted"] == 2
    sql = mock_cursor.execute.call_args[0][0]
    assert "LIKE" in sql


def test_rag_query_includes_usage_when_present(client):

    with patch("docpipe.rag.pipeline.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="answer",
            usage_metadata={"input_tokens": 11, "output_tokens": 4, "total_tokens": 15},
        )
        mock_create_llm.return_value = mock_llm

        with (
            patch("docpipe.rag.pipeline.RAGPipeline._create_embeddings") as mock_emb,
            patch("docpipe.rag.pipeline.RAGPipeline._get_vectorstore") as mock_vs,
        ):
            mock_emb.return_value = MagicMock()
            mock_vs.return_value = MagicMock(
                similarity_search_with_score=MagicMock(return_value=[])
            )
            resp = client.post(
                "/rag/query",
                json={
                    "question": "What is X?",
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
                },
            )
    assert resp.status_code == 200
    usage = resp.json().get("usage")
    assert usage is not None
    assert usage["input_tokens"] == 11


@patch("docpipe.vectorstores.factory.list_collection_sources")
def test_list_collection_sources_endpoint(mock_list, client):
    mock_list.return_value = (
        [
            {
                "source": "https://minio/a.pdf",
                "chunk_count": 3,
                "document_id": "uuid-1",
                "document_title": "A.pdf",
            },
        ],
        3,
    )
    resp = client.post(
        "/collection/sources",
        json={
            "connection_string": "postgresql://test/db",
            "table_name": "docpipe_abc",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["table_name"] == "docpipe_abc"
    assert body["total_chunks"] == 3
    assert len(body["sources"]) == 1
    assert body["sources"][0]["document_title"] == "A.pdf"


def test_generate_llm_error_returns_500(client):
    with patch("docpipe.rag.pipeline.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("provider timeout")
        mock_create_llm.return_value = mock_llm

        resp = client.post(
            "/generate",
            json={
                "prompt": "hello",
                "llm_provider": "openai",
                "llm_model": "gpt-4o-mini",
            },
        )
    assert resp.status_code == 500
