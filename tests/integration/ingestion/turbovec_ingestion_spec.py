"""End-to-end ingestion through the public facade and TurboVec plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import DocumentFormat, IngestionConfig, ParsedDocument
from docpipe.ingestion.pipeline import IngestionPipeline

pytest.importorskip("turbovec")

pytestmark = pytest.mark.requires_turbovec


class ExactEmbeddings:
    """Deterministic eight-dimensional embedding double."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] * 8 for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0] * 8


class IdentityChunker:
    """Return legacy boundary documents unchanged."""

    def split_documents(self, documents: list[object]) -> list[object]:
        return documents


def test_public_facade_persists_through_turbovec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        from turbovec import IdMapIndex  # noqa: F401
    except ImportError:
        pytest.skip("TurboVec is not installed")
    monkeypatch.setattr(
        IngestionPipeline,
        "_create_embeddings",
        staticmethod(lambda config: ExactEmbeddings()),
    )
    monkeypatch.setattr(
        IngestionPipeline,
        "_create_chunker",
        staticmethod(lambda config: IdentityChunker()),
    )
    config = IngestionConfig(
        connection_string="unused",
        table_name="documents",
        embedding_provider="test",
        embedding_model="exact",
        vector_backend="turbovec",
        turbovec_index_dir=str(tmp_path),
        write_batch_size=1,
    )
    parsed = ParsedDocument(
        source="report.pdf",
        format=DocumentFormat.PDF,
        text="persist me",
    )

    result = IngestionPipeline(config).ingest(parsed)

    assert result.chunks_ingested == 1
    assert result.table_created
    assert (tmp_path / "documents" / "index.tvim").is_file()
    assert (tmp_path / "documents" / "docstore.json").is_file()


@pytest.mark.asyncio
async def test_legacy_rollback_facade_persists_through_turbovec_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the documented legacy rollback usable with the supported 1.x API."""
    monkeypatch.setattr(
        IngestionPipeline,
        "_create_embeddings",
        staticmethod(lambda config: ExactEmbeddings()),
    )
    monkeypatch.setattr(
        IngestionPipeline,
        "_create_chunker",
        staticmethod(lambda config: IdentityChunker()),
    )
    settings = DocpipeSettings(
        plugin_foundation_enabled=False,
        turbovec_index_dir=str(tmp_path),
    )
    runtime = build_runtime(settings)
    config = IngestionConfig(
        connection_string="unused",
        table_name="documents",
        embedding_provider="test",
        embedding_model="exact",
        vector_backend="turbovec",
        turbovec_index_dir=str(tmp_path),
        write_batch_size=1,
    )
    parsed = ParsedDocument(
        source="rollback-report.pdf",
        format=DocumentFormat.PDF,
        text="persist through the rollback path",
    )

    async with runtime:
        pipeline = IngestionPipeline(config, runtime=runtime)
        result = await pipeline.aingest(parsed)

    assert result.chunks_ingested == 1
    assert (tmp_path / "documents" / "index.tvim").is_file()
    assert (tmp_path / "documents" / "docstore.json").is_file()
