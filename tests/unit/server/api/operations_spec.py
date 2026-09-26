"""Basic health, metrics, and source aggregation endpoint behavior."""

from __future__ import annotations

from unittest.mock import patch


def should_report_health_dependencies(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "dependencies" in response.json()


def should_expose_metrics(client) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "docpipe" in response.text or "python_info" in response.text


@patch("docpipe.server.services.ingest.list_collection_sources")
def should_list_legacy_collection_sources(list_sources, client) -> None:
    list_sources.return_value = (
        [
            {
                "source": "https://minio/a.pdf",
                "chunk_count": 3,
                "document_id": "uuid-1",
                "document_title": "A.pdf",
            }
        ],
        3,
    )
    response = client.post(
        "/collection/sources",
        json={"connection_string": "postgresql://test/db", "table_name": "docpipe_abc"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["table_name"] == "docpipe_abc"
    assert body["total_chunks"] == 3
    assert len(body["sources"]) == 1
    assert body["sources"][0]["document_title"] == "A.pdf"
