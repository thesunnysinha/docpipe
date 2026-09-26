"""Tests for vendor-neutral ingestion document construction."""

from __future__ import annotations

from docpipe.core.types import (
    DocumentFormat,
    ExtractionResult,
    PageContent,
    ParsedDocument,
)
from docpipe.ingestion.configuration import IngestMode
from docpipe.ingestion.document_builder import DocumentBuilder, IngestionDocument


def test_builder_emits_docpipe_documents_for_pages_and_extractions() -> None:
    parsed = ParsedDocument(
        source="report.pdf",
        format=DocumentFormat.PDF,
        text="complete report",
        pages=[
            PageContent(page_number=1, text="first page"),
            PageContent(page_number=2, text="  "),
        ],
    )
    extraction = ExtractionResult(
        entity_class="invoice",
        text="INV-42",
        attributes={"amount": 10},
    )

    documents = DocumentBuilder(IngestMode.BOTH).build(parsed, (extraction,))

    assert all(isinstance(document, IngestionDocument) for document in documents)
    assert [document.text for document in documents] == ["first page", "invoice: INV-42"]
    assert documents[0].metadata == {
        "source": "report.pdf",
        "page": 1,
        "source_type": "parsed",
    }
    assert documents[1].metadata["amount"] == 10
    assert documents[0].record_id != documents[1].record_id


def test_builder_falls_back_to_document_text_and_ids_are_deterministic() -> None:
    parsed = ParsedDocument(
        source="blank-pages.pdf",
        format=DocumentFormat.PDF,
        text="fallback text",
        pages=[PageContent(page_number=1, text="")],
    )
    builder = DocumentBuilder(IngestMode.CHUNKS)

    first = builder.build(parsed)
    second = builder.build(parsed)

    assert len(first) == 1
    assert first[0].text == "fallback text"
    assert first[0].record_id == second[0].record_id
    assert first[0].__class__.__module__ == "docpipe.ingestion.document_builder"


def test_builder_returns_no_documents_for_empty_selected_content() -> None:
    parsed = ParsedDocument(
        source="empty.txt",
        format=DocumentFormat.TEXT,
        text="",
    )

    assert DocumentBuilder(IngestMode.CHUNKS).build(parsed) == ()
    assert DocumentBuilder(IngestMode.EXTRACTIONS).build(parsed, ()) == ()
