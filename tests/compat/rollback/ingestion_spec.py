"""The temporary rollback switch bypasses vector-plugin selection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import DocumentFormat, IngestionConfig, IngestionResult, ParsedDocument
from docpipe.ingestion.pipeline import IngestionPipeline


@pytest.mark.asyncio
async def should_use_legacy_ingestion_when_plugin_foundation_is_disabled() -> None:
    runtime = build_runtime(DocpipeSettings(plugin_foundation_enabled=False))
    config = IngestionConfig(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="embedding",
    )
    parsed = ParsedDocument(source="document.txt", format=DocumentFormat.TEXT, text="content")
    expected = IngestionResult(
        source="document.txt", chunks_ingested=1, table_name="docs", table_created=True
    )
    with (
        patch.object(IngestionPipeline, "_create_embeddings", return_value=MagicMock()),
        patch.object(IngestionPipeline, "_create_chunker", return_value=MagicMock()),
        patch("docpipe.ingestion.pipeline.build_ingestion_coordinator") as build_new,
        patch("docpipe.ingestion.pipeline.LegacyIngestionExecutor") as legacy,
    ):
        legacy.return_value.ingest.return_value = expected
        async with runtime:
            result = await IngestionPipeline(config, runtime=runtime).aingest(parsed)

    assert result == expected
    build_new.assert_not_called()
    legacy.return_value.ingest.assert_called_once_with(parsed, None)
