"""Compatibility snapshots for the public ingestion facade."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.core.errors import IngestionError
from docpipe.core.types import (
    DocumentFormat,
    IngestionConfig,
    IngestionResult,
    ParsedDocument,
)
from docpipe.ingestion.pipeline import IngestionPipeline
from docpipe.server.app import create_app
from docpipe.server.services.ingest import IngestService


def _config(*, contextual_injection: bool = False) -> IngestionConfig:
    return IngestionConfig(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        contextual_injection=contextual_injection,
    )


def _parsed() -> ParsedDocument:
    return ParsedDocument(
        source="document.pdf",
        format=DocumentFormat.PDF,
        text="document text",
    )


@patch.object(IngestionPipeline, "_create_chunker", return_value=MagicMock())
@patch.object(IngestionPipeline, "_create_embeddings", return_value=MagicMock())
@patch("docpipe.ingestion.pipeline.build_ingestion_coordinator")
def test_sync_facade_preserves_result_shape(
    build: MagicMock,
    embeddings: MagicMock,
    chunker: MagicMock,
) -> None:
    expected = IngestionResult(
        source="document.pdf",
        chunks_ingested=3,
        skipped=0,
        table_name="docs",
        table_created=True,
    )
    build.return_value.ingest = AsyncMock(return_value=expected)

    result = IngestionPipeline(_config()).ingest(_parsed())

    assert result.model_dump() == expected.model_dump()
    build.return_value.ingest.assert_awaited_once()


@patch.object(IngestionPipeline, "_create_chunker", return_value=MagicMock())
@patch.object(IngestionPipeline, "_create_embeddings", return_value=MagicMock())
@patch("docpipe.ingestion.pipeline.build_ingestion_coordinator")
def test_sync_facade_preserves_ingestion_error_type(
    build: MagicMock,
    embeddings: MagicMock,
    chunker: MagicMock,
) -> None:
    build.return_value.ingest = AsyncMock(side_effect=IngestionError("write failed"))

    with pytest.raises(IngestionError, match="write failed"):
        IngestionPipeline(_config()).ingest(_parsed())


@pytest.mark.parametrize("enabled", [False, True])
@patch.object(IngestionPipeline, "_create_chunker", return_value=MagicMock())
@patch.object(IngestionPipeline, "_create_embeddings", return_value=MagicMock())
@patch.object(IngestionPipeline, "_create_context_llm", return_value=MagicMock())
@patch("docpipe.ingestion.pipeline.build_ingestion_coordinator")
def test_contextualization_selection_is_preserved(
    build: MagicMock,
    context_llm: MagicMock,
    embeddings: MagicMock,
    chunker: MagicMock,
    enabled: bool,
) -> None:
    build.return_value.ingest = AsyncMock(
        return_value=IngestionResult(
            source="document.pdf",
            chunks_ingested=1,
            table_name="docs",
            table_created=True,
        )
    )

    IngestionPipeline(_config(contextual_injection=enabled)).ingest(_parsed())

    assert (build.call_args.kwargs["contextualizer"] is not None) is enabled
    assert context_llm.called is enabled


def _request() -> dict[str, object]:
    return {
        "source": "document.pdf",
        "connection_string": "postgresql://test/db",
        "table_name": "docs",
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
    }


@patch.object(IngestionPipeline, "_create_chunker", return_value=MagicMock())
@patch.object(IngestionPipeline, "_create_embeddings", return_value=MagicMock())
@patch.object(IngestionPipeline, "aingest")
@patch.object(IngestService, "_resolve_and_parse")
def test_http_facade_preserves_success_shape(
    resolve: AsyncMock,
    aingest: AsyncMock,
    embeddings: MagicMock,
    chunker: MagicMock,
) -> None:
    resolve.return_value = ({"chunker": "recursive"}, "mock", _parsed())
    aingest.return_value = IngestionResult(
        source="document.pdf",
        chunks_ingested=2,
        table_name="docs",
        table_created=True,
    )

    with TestClient(create_app()) as client:
        response = client.post("/ingest", json=_request())

    assert response.status_code == 200
    assert response.json() == {
        "source": "document.pdf",
        "chunks_ingested": 2,
        "skipped": 0,
        "table_name": "docs",
        "table_created": True,
        "lightrag_synced": False,
    }


@patch.object(IngestionPipeline, "_create_chunker", return_value=MagicMock())
@patch.object(IngestionPipeline, "_create_embeddings", return_value=MagicMock())
@patch.object(IngestionPipeline, "aingest", new_callable=AsyncMock)
@patch.object(IngestService, "_resolve_and_parse", new_callable=AsyncMock)
def test_http_facade_preserves_ingestion_error_mapping(
    resolve: AsyncMock,
    aingest: AsyncMock,
    embeddings: MagicMock,
    chunker: MagicMock,
) -> None:
    resolve.return_value = ({"chunker": "recursive"}, "mock", _parsed())
    aingest.side_effect = IngestionError("vector store write failed")

    with TestClient(create_app()) as client:
        response = client.post("/ingest", json=_request())

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "message": "vector store write failed",
        "error_type": "docpipe",
        "phase": "embedding",
    }
