"""Tests for GLM-OCR parser integration."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.types import DocumentFormat, ParsedDocument

# ---------------------------------------------------------------------------
# Fake glmocr module (not installed in dev)
# ---------------------------------------------------------------------------

def _make_fake_glmocr() -> ModuleType:
    mod = ModuleType("glmocr")

    class FakeResult:
        def __init__(self) -> None:
            self.text = "Parsed text from GLM-OCR"
            self.markdown = "# Parsed markdown from GLM-OCR"
            self.pages = [
                {"text": "Page 1 content"},
                {"text": "Page 2 content"},
            ]

    class FakeGLMOCR:
        def __init__(self, **kwargs: object) -> None:
            pass

        def run(self, source: str, **kwargs: object) -> FakeResult:
            return FakeResult()

    mod.GLMOCR = FakeGLMOCR  # type: ignore[attr-defined]
    return mod


fake_glmocr = _make_fake_glmocr()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGLMOCRParser:
    """Test suite for GLMOCRParser."""

    def test_is_available_when_installed(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            assert GLMOCRParser.is_available() is True

    def test_is_available_when_not_installed(self) -> None:
        with patch.dict(sys.modules, {"glmocr": None}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            assert GLMOCRParser.is_available() is False

    def test_parse_returns_parsed_document(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            parser = GLMOCRParser()
            result = parser.parse("test.pdf")

            assert isinstance(result, ParsedDocument)
            assert result.source == "test.pdf"
            assert result.text == "Parsed text from GLM-OCR"
            assert result.markdown == "# Parsed markdown from GLM-OCR"
            assert result.format == DocumentFormat.PDF
            assert result.metadata["parser"] == "glm-ocr"

    def test_parse_extracts_pages(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            parser = GLMOCRParser()
            result = parser.parse("test.pdf")

            assert len(result.pages) == 2
            assert result.pages[0].page_number == 1
            assert result.pages[0].text == "Page 1 content"
            assert result.pages[1].page_number == 2

    def test_parse_batch(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            parser = GLMOCRParser()
            results = parser.parse_batch(["a.pdf", "b.pdf"])

            assert len(results) == 2
            assert results[0].source == "a.pdf"
            assert results[1].source == "b.pdf"

    def test_supported_formats(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            formats = GLMOCRParser.supported_formats()
            assert "pdf" in formats
            assert "image" in formats

    def test_detect_format(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            assert GLMOCRParser._detect_format("doc.pdf") == DocumentFormat.PDF
            assert GLMOCRParser._detect_format("photo.png") == DocumentFormat.IMAGE
            assert GLMOCRParser._detect_format("page.html") == DocumentFormat.HTML
            assert GLMOCRParser._detect_format("unknown.xyz") == DocumentFormat.TEXT

    def test_parse_error_handling(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.core.errors import ParseError
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            parser = GLMOCRParser()
            parser._ocr.run = MagicMock(side_effect=RuntimeError("OCR failed"))

            with pytest.raises(ParseError, match="GLM-OCR"):
                parser.parse("bad.pdf")

    def test_name_attribute(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser

            assert GLMOCRParser.name == "glm-ocr"


class TestGLMOCRRegistration:
    """Test that GLM-OCR is registered in the plugin registry."""

    def test_registry_discovers_glm_ocr(self) -> None:
        with patch.dict(sys.modules, {"glmocr": fake_glmocr}):
            from docpipe.parsers.glm_ocr_parser import GLMOCRParser
            from docpipe.registry.registry import PluginRegistry

            registry = PluginRegistry.get()
            registry.register_parser("glm-ocr", GLMOCRParser)

            assert "glm-ocr" in registry.list_parsers()

            parser = registry.get_parser("glm-ocr")
            result = parser.parse("test.pdf")
            assert isinstance(result, ParsedDocument)
