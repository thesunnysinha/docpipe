"""Source security remains active when vector-store rollback is enabled."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import DocumentFormat, ParsedDocument
from docpipe.plugins.errors import UnsafeSourceError
from docpipe.sources.parsing import SourceParser


def _parsed() -> ParsedDocument:
    return ParsedDocument(source="document.txt", format=DocumentFormat.TEXT, text="content")


def should_default_to_the_plugin_path_and_accept_env_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DOCPIPE_PLUGIN_FOUNDATION_ENABLED", raising=False)
    assert DocpipeSettings(_env_file=None).plugin_foundation_enabled
    monkeypatch.setenv("DOCPIPE_PLUGIN_FOUNDATION_ENABLED", "false")
    assert not DocpipeSettings(_env_file=None).plugin_foundation_enabled


@pytest.mark.asyncio
async def should_keep_source_root_policy_during_vector_rollback(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = allowed / "document.txt"
    source.write_text("document", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    runtime = build_runtime(
        DocpipeSettings(
            plugin_foundation_enabled=False,
            source_allowed_roots=(allowed,),
        )
    )
    parser = SimpleNamespace(aparse=AsyncMock(return_value=_parsed()))

    async with runtime:
        result = await SourceParser(runtime).parse(parser, str(source))
        with pytest.raises(UnsafeSourceError):
            await SourceParser(runtime).parse(parser, str(outside))

    assert result.text == "content"
    assert result.source == str(source.resolve())
    parser.aparse.assert_awaited_once_with(str(source.resolve()))
