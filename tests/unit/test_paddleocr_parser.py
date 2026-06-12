"""PaddleOCR parser contract tests (mocked)."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from docpipe.parsers.paddleocr_parser import PaddleOCRParser


def _fake_paddleocr_module(engine: MagicMock) -> ModuleType:
    mod = ModuleType("paddleocr")
    mod.PPStructureV3 = MagicMock(return_value=engine)
    return mod


@patch("docpipe.parsers.paddleocr_parser.assert_safe_http_source")
def test_paddleocr_parser_predict_dict(_ssrf: MagicMock) -> None:
    engine = MagicMock()
    engine.predict.return_value = {"markdown": "# OCR text", "text": "OCR text"}
    fake = _fake_paddleocr_module(engine)

    with (
        patch.dict(sys.modules, {"paddleocr": fake}),
        patch.object(PaddleOCRParser, "is_available", return_value=True),
    ):
        parser = PaddleOCRParser()
        doc = parser.parse("/tmp/scan.pdf")

    assert doc.text == "# OCR text"
    assert doc.metadata["parser"] == "paddleocr"
    engine.predict.assert_called_once()
