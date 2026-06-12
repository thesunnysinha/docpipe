"""MinerU parser contract tests (mocked — no GPU)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.errors import ParseError


def _fake_mineru_module() -> ModuleType:
    mod = ModuleType("mineru")
    cli = ModuleType("mineru.cli")
    common = ModuleType("mineru.cli.common")
    mod.cli = cli
    cli.common = common
    return mod


def _write_mineru_output(**kwargs: object) -> None:
    out = Path(str(kwargs["output_dir"]))
    out.mkdir(parents=True, exist_ok=True)
    (out / "doc.md").write_text("# MinerU output\n\nHello world.", encoding="utf-8")


@patch("docpipe.parsers.mineru_parser.assert_safe_http_source")
def test_mineru_parser_reads_markdown(_ssrf: MagicMock) -> None:
    fake = _fake_mineru_module()
    fake.cli.common.do_parse = MagicMock(side_effect=_write_mineru_output)

    modules = {
        "mineru": fake,
        "mineru.cli": fake.cli,
        "mineru.cli.common": fake.cli.common,
    }
    with patch.dict(sys.modules, modules):
        from docpipe.parsers.mineru_parser import MinerUParser

        with patch.object(MinerUParser, "is_available", return_value=True):
            parser = MinerUParser()
            doc = parser.parse("/tmp/sample.pdf")

    assert "Hello world" in doc.text
    assert doc.metadata["parser"] == "mineru"


@patch("docpipe.parsers.mineru_parser.assert_safe_http_source")
def test_mineru_parser_raises_when_no_markdown(_ssrf: MagicMock) -> None:
    fake = _fake_mineru_module()
    fake.cli.common.do_parse = MagicMock(return_value=None)

    modules = {
        "mineru": fake,
        "mineru.cli": fake.cli,
        "mineru.cli.common": fake.cli.common,
    }
    with patch.dict(sys.modules, modules):
        from docpipe.parsers.mineru_parser import MinerUParser

        with patch.object(MinerUParser, "is_available", return_value=True):
            parser = MinerUParser()
            with pytest.raises(ParseError, match="no markdown"):
                parser.parse("/tmp/empty.pdf")
