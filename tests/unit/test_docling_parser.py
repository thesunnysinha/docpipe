"""Tests for Docling parser page extraction (dict pages, export_to_text per page)."""

from unittest.mock import MagicMock, patch

from docpipe.core.types import DocumentFormat
from docpipe.parsers.docling_parser import DoclingParser


def _mock_docling_document(*, pages: dict | None, full_text: str) -> MagicMock:
    doc = MagicMock()
    doc.pages = pages or {}
    doc.export_to_text.side_effect = lambda page_no=None, **kwargs: (
        f"Page {page_no} payslip text" if page_no is not None else full_text
    )
    doc.export_to_markdown.return_value = "# md"
    return doc


def test_parse_extracts_text_from_dict_pages() -> None:
    """Docling pages are dict[int, PageItem]; keys are not PageItem instances."""
    mock_doc = _mock_docling_document(
        pages={1: MagicMock(page_no=1), 2: MagicMock(page_no=2)},
        full_text="Full payslip body",
    )
    conv_result = MagicMock()
    conv_result.document = mock_doc
    conv_result.status.name = "SUCCESS"

    with (
        patch.object(DoclingParser, "is_available", return_value=True),
        patch.object(DoclingParser, "__init__", lambda self, **kwargs: None),
    ):
        parser = DoclingParser()
        parser._converter = MagicMock()
        parser._converter.convert.return_value = conv_result
        result = parser.parse("http://minio/bucket/payslip.pdf")

    assert result.text == "Full payslip body"
    assert len(result.pages) == 2
    assert result.pages[0].page_number == 1
    assert "Page 1" in result.pages[0].text
    assert result.pages[1].page_number == 2
    mock_doc.export_to_text.assert_any_call(page_no=1)
    mock_doc.export_to_text.assert_any_call(page_no=2)


def test_parse_falls_back_to_full_text_when_page_export_empty() -> None:
    mock_doc = _mock_docling_document(
        pages={1: MagicMock(page_no=1)},
        full_text="Payslip net pay $5000",
    )
    mock_doc.export_to_text.side_effect = lambda page_no=None, **kwargs: (
        "" if page_no is not None else "Payslip net pay $5000"
    )
    conv_result = MagicMock()
    conv_result.document = mock_doc
    conv_result.status.name = "SUCCESS"

    with (
        patch.object(DoclingParser, "is_available", return_value=True),
        patch.object(DoclingParser, "__init__", lambda self, **kwargs: None),
    ):
        parser = DoclingParser()
        parser._converter = MagicMock()
        parser._converter.convert.return_value = conv_result
        result = parser.parse("payslip.pdf")

    assert len(result.pages) == 1
    assert result.pages[0].text == "Payslip net pay $5000"
    assert result.format == DocumentFormat.PDF
