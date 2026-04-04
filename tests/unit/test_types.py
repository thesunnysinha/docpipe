"""Tests for core Pydantic models."""

from docpipe.core.types import (
    DocumentFormat,
    ExtractionResult,
    ExtractionSchema,
    IngestionConfig,
    IngestionResult,
    PageContent,
    ParsedDocument,
    PipelineResult,
    SourceSpan,
)


def test_parsed_document_creation():
    doc = ParsedDocument(
        source="test.pdf",
        format=DocumentFormat.PDF,
        text="Hello world",
        markdown="# Hello\n\nworld",
    )
    assert doc.source == "test.pdf"
    assert doc.format == DocumentFormat.PDF
    assert doc.text == "Hello world"
    assert doc.metadata == {}
    assert doc.pages == []


def test_parsed_document_with_pages():
    doc = ParsedDocument(
        source="test.pdf",
        format=DocumentFormat.PDF,
        text="Page 1\nPage 2",
        pages=[
            PageContent(page_number=1, text="Page 1"),
            PageContent(page_number=2, text="Page 2"),
        ],
    )
    assert len(doc.pages) == 2
    assert doc.pages[0].page_number == 1


def test_parsed_document_serialization():
    doc = ParsedDocument(
        source="test.pdf",
        format=DocumentFormat.PDF,
        text="Hello",
        raw={"should": "be excluded"},
    )
    data = doc.model_dump()
    assert "raw" not in data
    assert data["source"] == "test.pdf"


def test_extraction_result():
    result = ExtractionResult(
        entity_class="person",
        text="John Doe",
        attributes={"age": 30},
        source_span=SourceSpan(start=0, end=8),
        confidence=0.95,
    )
    assert result.entity_class == "person"
    assert result.source_span.start == 0
    assert result.confidence == 0.95


def test_extraction_result_without_span():
    result = ExtractionResult(entity_class="date", text="2024-01-01")
    assert result.source_span is None
    assert result.confidence is None
    assert result.attributes == {}


def test_extraction_schema():
    schema = ExtractionSchema(
        description="Extract entities",
        model_id="gemini-2.5-flash",
        entity_classes=["person", "org"],
        examples=[{"text": "John works at Acme", "extractions": []}],
    )
    assert schema.model_id == "gemini-2.5-flash"
    assert len(schema.entity_classes) == 2


def test_pipeline_result():
    parsed = ParsedDocument(
        source="test.pdf", format=DocumentFormat.PDF, text="Hello"
    )
    result = PipelineResult(
        source="test.pdf",
        parsed=parsed,
        extractions=[
            ExtractionResult(entity_class="test", text="hello")
        ],
    )
    assert result.source == "test.pdf"
    assert len(result.extractions) == 1


def test_ingestion_config():
    config = IngestionConfig(
        connection_string="postgresql://user:pass@localhost/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )
    assert config.chunk_size == 1000
    assert config.chunk_overlap == 200
    assert config.ingest_mode == "both"


def test_ingestion_result():
    result = IngestionResult(
        source="test.pdf",
        chunks_ingested=42,
        table_name="docs",
        table_created=True,
    )
    assert result.chunks_ingested == 42
    assert result.table_created is True


def test_document_format_values():
    assert DocumentFormat.PDF == "pdf"
    assert DocumentFormat.DOCX == "docx"
    assert DocumentFormat.IMAGE == "image"
