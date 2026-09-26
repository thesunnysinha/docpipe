"""Rollback executor keeps legacy writes bounded and errors safe."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.core.errors import ConfigurationError, IngestionError
from docpipe.core.types import DocumentFormat, IngestionConfig, ParsedDocument
from docpipe.ingestion.legacy_executor import LegacyIngestionExecutor


def _config(**overrides: object) -> IngestionConfig:
    values: dict[str, object] = {
        "connection_string": "postgresql://test/db",
        "table_name": "docs",
        "embedding_provider": "openai",
        "embedding_model": "embedding",
    }
    values.update(overrides)
    return IngestionConfig.model_validate(values)


def _parsed() -> ParsedDocument:
    return ParsedDocument(source="file.txt", format=DocumentFormat.TEXT, text="content")


def _executor(config: IngestionConfig, chunker: MagicMock) -> LegacyIngestionExecutor:
    return LegacyIngestionExecutor(
        config,
        embeddings=MagicMock(),
        chunker=chunker,
        context_llm_factory=MagicMock(),
    )


def should_write_chunked_documents_without_loading_a_vector_plugin() -> None:
    source = MagicMock(metadata={"source": "file.txt"})
    chunk = MagicMock(metadata={"source": "file.txt"})
    chunker = MagicMock()
    chunker.split_documents.return_value = [chunk]
    with (
        patch("docpipe.ingestion.legacy_executor.parsed_to_langchain", return_value=[source]),
        patch("docpipe.ingestion.legacy_executor.ingest_documents") as write,
    ):
        result = _executor(_config(chunk_metadata={"kind": "report"}), chunker).ingest(_parsed())

    assert result.chunks_ingested == 1
    assert result.table_created
    assert chunk.metadata["kind"] == "report"
    write.assert_called_once()


def should_reject_namespaced_vector_provider_in_legacy_mode() -> None:
    config = _config(vector_store=VectorStoreOptions(provider="qdrant"))
    with pytest.raises(ConfigurationError, match="vector_store requires"):
        _executor(config, MagicMock()).ingest(_parsed())


def should_not_leak_vendor_errors_from_legacy_writes() -> None:
    vendor_message = "secret-token-1234"
    chunker = MagicMock()
    chunker.split_documents.return_value = [MagicMock(metadata={})]
    with (
        patch("docpipe.ingestion.legacy_executor.parsed_to_langchain", return_value=[MagicMock()]),
        patch(
            "docpipe.ingestion.legacy_executor.ingest_documents",
            side_effect=Exception(vendor_message),
        ),
        pytest.raises(IngestionError) as failure,
    ):
        _executor(_config(), chunker).ingest(_parsed())

    assert vendor_message not in str(failure.value)
