"""Tests for ingestion pipeline (mocked)."""

from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.types import (
    DocumentFormat,
    ExtractionResult,
    IngestionConfig,
    ParsedDocument,
    SourceSpan,
)


def _make_parsed_doc(text: str = "Test content") -> ParsedDocument:
    return ParsedDocument(
        source="test.pdf",
        format=DocumentFormat.PDF,
        text=text,
        markdown=f"# Test\n\n{text}",
    )


def _make_config() -> IngestionConfig:
    return IngestionConfig(
        connection_string="postgresql://test:test@localhost/test",
        table_name="test_docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )


def _make_extractions() -> list[ExtractionResult]:
    return [
        ExtractionResult(
            entity_class="person",
            text="John Doe",
            attributes={"age": 30},
            source_span=SourceSpan(start=0, end=8),
        )
    ]


@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_embeddings")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_splitter")
def test_parsed_to_lc_docs(mock_splitter, mock_embeddings):
    from docpipe.ingestion.pipeline import IngestionPipeline

    mock_embeddings.return_value = MagicMock()
    mock_splitter.return_value = MagicMock()

    pipeline = IngestionPipeline(_make_config())
    docs = pipeline._parsed_to_lc_docs(_make_parsed_doc())

    assert len(docs) == 1
    assert docs[0].page_content == "Test content"
    assert docs[0].metadata["source"] == "test.pdf"
    assert docs[0].metadata["source_type"] == "parsed"


@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_embeddings")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_splitter")
def test_extractions_to_lc_docs(mock_splitter, mock_embeddings):
    from docpipe.ingestion.pipeline import IngestionPipeline

    mock_embeddings.return_value = MagicMock()
    mock_splitter.return_value = MagicMock()

    pipeline = IngestionPipeline(_make_config())
    extractions = _make_extractions()
    docs = pipeline._extractions_to_lc_docs(extractions, "test.pdf")

    assert len(docs) == 1
    assert "person: John Doe" in docs[0].page_content
    assert docs[0].metadata["source_type"] == "extraction"
    assert docs[0].metadata["entity_class"] == "person"
