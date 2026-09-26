"""Tests for ingestion pipeline (mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

from docpipe.core.types import (
    DocumentFormat,
    ExtractionResult,
    IngestionConfig,
    PageContent,
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
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_chunker")
def test_parsed_to_lc_docs(mock_chunker, mock_embeddings):
    from docpipe.ingestion.pipeline import IngestionPipeline

    mock_embeddings.return_value = MagicMock()
    mock_chunker.return_value = MagicMock()

    pipeline = IngestionPipeline(_make_config())
    docs = pipeline._parsed_to_lc_docs(_make_parsed_doc())

    assert len(docs) == 1
    assert docs[0].page_content == "Test content"
    assert docs[0].metadata["source"] == "test.pdf"
    assert docs[0].metadata["source_type"] == "parsed"


@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_embeddings")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_chunker")
def test_parsed_to_lc_docs_empty_pages_falls_back_to_document_text(mock_chunker, mock_embeddings):
    """When page metadata exists but page texts are blank, use parsed.text."""
    from docpipe.ingestion.pipeline import IngestionPipeline

    mock_embeddings.return_value = MagicMock()
    mock_chunker.return_value = MagicMock()

    parsed = ParsedDocument(
        source="payslip.pdf",
        format=DocumentFormat.PDF,
        text="Net pay: $4,200.00",
        pages=[
            PageContent(page_number=1, text=""),
            PageContent(page_number=2, text="   "),
        ],
    )
    pipeline = IngestionPipeline(_make_config())
    docs = pipeline._parsed_to_lc_docs(parsed)

    assert len(docs) == 1
    assert docs[0].page_content == "Net pay: $4,200.00"


@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_embeddings")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_chunker")
def test_extractions_to_lc_docs(mock_chunker, mock_embeddings):
    from docpipe.ingestion.pipeline import IngestionPipeline

    mock_embeddings.return_value = MagicMock()
    mock_chunker.return_value = MagicMock()

    pipeline = IngestionPipeline(_make_config())
    extractions = _make_extractions()
    docs = pipeline._extractions_to_lc_docs(extractions, "test.pdf")

    assert len(docs) == 1
    assert "person: John Doe" in docs[0].page_content
    assert docs[0].metadata["source_type"] == "extraction"
    assert docs[0].metadata["entity_class"] == "person"


@patch("docpipe.ingestion.pipeline.build_ingestion_coordinator")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_embeddings")
@patch("docpipe.ingestion.pipeline.IngestionPipeline._create_chunker")
def test_ingest_delegates_with_chunk_metadata(mock_chunker, mock_embeddings, mock_build):
    from docpipe.core.types import IngestionResult
    from docpipe.ingestion.pipeline import IngestionPipeline

    mock_embeddings.return_value = MagicMock()
    mock_chunker.return_value = MagicMock()
    coordinator = mock_build.return_value
    coordinator.ingest = AsyncMock(
        return_value=IngestionResult(
            source="test.pdf",
            chunks_ingested=1,
            table_name="test_docs",
            table_created=True,
        )
    )

    config = _make_config()
    config.chunk_metadata = {
        "document_id": "doc-uuid",
        "document_title": "My Doc",
    }
    pipeline = IngestionPipeline(config)
    result = pipeline.ingest(_make_parsed_doc(), extractions=None)

    assert result.chunks_ingested == 1
    passed_config = mock_build.call_args.args[0]
    assert passed_config.chunk_metadata["document_id"] == "doc-uuid"
    assert passed_config.chunk_metadata["document_title"] == "My Doc"
    coordinator.ingest.assert_awaited_once()
