"""Tests for MarkItDown parser adapter."""

from unittest.mock import MagicMock, patch

from docpipe.core.types import DocumentFormat
from docpipe.parsers.markitdown_parser import MarkItDownParser


def _mock_result(*, markdown: str = "# Title", text: str = "Body text", title: str | None = "Doc"):
    result = MagicMock()
    result.markdown = markdown
    result.text_content = text
    result.title = title
    return result


def test_parse_local_file_uses_convert_local() -> None:
    with (
        patch.object(MarkItDownParser, "is_available", return_value=True),
        patch.object(MarkItDownParser, "__init__", lambda self, **kwargs: None),
        patch("pathlib.Path.exists", return_value=True),
    ):
        parser = MarkItDownParser()
        parser._converter = MagicMock()
        parser._converter.convert_local.return_value = _mock_result()

        result = parser.parse("/tmp/invoice.pdf")

    parser._converter.convert_local.assert_called_once()
    assert result.format == DocumentFormat.PDF
    assert result.markdown == "# Title"
    assert result.text == "Body text"
    assert result.metadata["parser"] == "markitdown"
    assert len(result.pages) == 1


def test_parse_url_uses_convert() -> None:
    with (
        patch.object(MarkItDownParser, "is_available", return_value=True),
        patch.object(MarkItDownParser, "__init__", lambda self, **kwargs: None),
        patch("pathlib.Path.exists", return_value=False),
    ):
        parser = MarkItDownParser()
        parser._converter = MagicMock()
        parser._converter.convert.return_value = _mock_result(text="Remote body")

        result = parser.parse("https://example.com/report.pdf")

    parser._converter.convert.assert_called_once_with("https://example.com/report.pdf")
    assert result.text == "Remote body"


def test_supported_formats_includes_office_and_media() -> None:
    formats = MarkItDownParser.supported_formats()
    assert "pdf" in formats
    assert "audio" in formats
    assert "zip" in formats
