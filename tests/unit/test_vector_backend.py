"""Vector backend routing (pgvector default, optional turbovec)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.types import IngestionConfig
from docpipe.vectorstores.base import resolve_vector_backend
from docpipe.vectorstores.factory import create_vectorstore, ingest_documents


def test_resolve_vector_backend_defaults_pgvector():
    assert resolve_vector_backend() == "pgvector"
    assert resolve_vector_backend(config="turbovec") == "turbovec"
    assert resolve_vector_backend(request="turbovec", config="pgvector") == "turbovec"


def test_resolve_vector_backend_invalid():
    with pytest.raises(ValueError, match="vector_backend"):
        resolve_vector_backend(config="faiss")


@patch("docpipe.vectorstores.factory._pgvector_class")
def test_create_vectorstore_pgvector(mock_pgvector_cls):
    embeddings = MagicMock()
    mock_pg_class = MagicMock()
    mock_pgvector_cls.return_value = mock_pg_class
    mock_instance = MagicMock()
    mock_pg_class.return_value = mock_instance

    store = create_vectorstore(
        embeddings=embeddings,
        table_name="my_docs",
        connection_string="postgresql://localhost/db",
        vector_backend="pgvector",
    )

    mock_pgvector_cls.assert_called_once()
    mock_pg_class.assert_called_once_with(
        embeddings=embeddings,
        collection_name="my_docs",
        connection="postgresql://localhost/db",
    )
    assert store is mock_instance


@patch("docpipe.vectorstores.factory.ingest_documents_turbovec")
@patch("docpipe.vectorstores.factory._pgvector_class")
def test_ingest_documents_routes_pgvector(mock_pgvector_cls, mock_turbovec_ingest):
    embeddings = MagicMock()
    docs = [MagicMock()]
    mock_pgvector_cls.return_value = MagicMock()

    ingest_documents(
        documents=docs,
        embeddings=embeddings,
        table_name="docs",
        connection_string="postgresql://localhost/db",
        vector_backend="pgvector",
    )

    mock_pgvector_cls.return_value.from_documents.assert_called_once()
    mock_turbovec_ingest.assert_not_called()


@patch("docpipe.vectorstores.factory.ingest_documents_turbovec")
@patch("docpipe.vectorstores.factory._pgvector_class")
def test_ingest_documents_routes_turbovec(mock_pgvector_cls, mock_turbovec_ingest):
    embeddings = MagicMock()
    docs = [MagicMock()]

    ingest_documents(
        documents=docs,
        embeddings=embeddings,
        table_name="docs",
        connection_string="postgresql://unused",
        vector_backend="turbovec",
        turbovec_index_dir="/tmp/indices",
    )

    mock_turbovec_ingest.assert_called_once()
    mock_pgvector_cls.return_value.from_documents.assert_not_called()


@patch("docpipe.ingestion.pipeline.ingest_documents")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_embeddings")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_chunker")
def test_ingestion_pipeline_uses_factory(mock_chunker, mock_embeddings, mock_ingest):
    from docpipe.ingestion.pipeline import IngestionPipeline

    mock_embeddings.return_value = MagicMock()
    splitter = MagicMock()
    chunk = MagicMock()
    chunk.page_content = "chunk"
    chunk.metadata = {}
    splitter.split_documents.return_value = [chunk]
    mock_chunker.return_value = splitter

    config = IngestionConfig(
        connection_string="postgresql://localhost/db",
        table_name="test_docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        vector_backend="pgvector",
    )
    pipeline = IngestionPipeline(config)
    result = pipeline.ingest(_make_parsed())

    mock_ingest.assert_called_once()
    assert result.chunks_ingested == 1
    assert result.table_name == "test_docs"


def _make_parsed():
    from docpipe.core.types import DocumentFormat, ParsedDocument

    return ParsedDocument(
        source="test.pdf",
        format=DocumentFormat.PDF,
        text="Hello world",
    )


@patch("docpipe.rag.pipeline.create_vectorstore")
@patch("docpipe.rag.pipeline.RAGPipeline._create_embeddings")
@patch("docpipe.rag.pipeline.RAGPipeline._create_llm")
def test_rag_get_vectorstore_pgvector(mock_llm, mock_embeddings, mock_create_vs):
    from docpipe.core.types import RAGConfig
    from docpipe.rag.pipeline import RAGPipeline

    mock_embeddings.return_value = MagicMock()
    mock_llm.return_value = MagicMock()
    mock_create_vs.return_value = MagicMock()

    config = RAGConfig(
        connection_string="postgresql://localhost/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        vector_backend="pgvector",
    )
    pipeline = RAGPipeline(config)
    vs = pipeline._get_vectorstore()

    mock_create_vs.assert_called_once()
    call_kwargs = mock_create_vs.call_args.kwargs
    assert call_kwargs["vector_backend"] == "pgvector"
    assert vs is mock_create_vs.return_value


@pytest.mark.requires_turbovec
def test_turbovec_import_optional():
    pytest.importorskip("turbovec")
    from turbovec.langchain import TurboQuantVectorStore  # noqa: F401

    assert TurboQuantVectorStore is not None


def test_delete_by_source_turbovec_docstore(tmp_path: Path):
    from docpipe.vectorstores.turbovec_store import (
        _docstore_entries,
        _entry_matches_source,
        turbovec_index_path,
    )

    table = "my_lib"
    path = turbovec_index_path(tmp_path, table)
    path.mkdir(parents=True)
    docstore = {
        "a": {"metadata": {"source": "file:///a.pdf"}, "page_content": "one"},
        "b": {"metadata": {"source": "file:///b.pdf"}, "page_content": "two"},
    }
    import json

    (path / "docstore.json").write_text(
        json.dumps({"docstore": docstore}),
        encoding="utf-8",
    )
    entries = _docstore_entries(path / "docstore.json")
    assert len(entries) == 2
    assert _entry_matches_source(
        docstore["a"], source="file:///a.pdf", source_contains=None, match_mode="exact"
    )
    assert _entry_matches_source(
        docstore["b"],
        source=None,
        source_contains="b.pdf",
        match_mode="contains",
    )
