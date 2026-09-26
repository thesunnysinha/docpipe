"""Parser compatibility over lifecycle-bound source handles."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.core.errors import ParseError
from docpipe.core.types import DocumentFormat, ParsedDocument
from docpipe.parsers.input_adapter import ParserInputAdapter
from docpipe.plugins.contracts.source import ManagedSourceHandle, SourceDescriptor


@pytest.fixture
async def runner() -> AsyncIterator[BoundedBlockingRunner]:
    async with BoundedBlockingRunner(max_concurrency=2) as bounded:
        yield bounded


def _parsed(source: str) -> ParsedDocument:
    return ParsedDocument(source=source, format=DocumentFormat.TEXT, text="parsed")


def _handle(
    path: Path,
    *,
    materialized: list[int],
    cleaned: list[int],
) -> ManagedSourceHandle:
    async def stream() -> AsyncIterator[bytes]:
        yield path.read_bytes()

    async def materialize() -> Path:
        materialized.append(1)
        return path

    async def cleanup() -> None:
        cleaned.append(1)

    return ManagedSourceHandle(
        SourceDescriptor("https://example.org/report.txt", "report.txt", "text/plain"),
        stream_factory=stream,
        materialize_factory=materialize,
        cleanup=cleanup,
    )


class PathParser:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    async def aparse(self, source: str) -> ParsedDocument:
        self.inputs.append(source)
        assert Path(source).is_file()
        return _parsed(source)


class HandleParser:
    def __init__(self) -> None:
        self.content = b""

    async def aparse_source(self, handle: ManagedSourceHandle) -> ParsedDocument:
        self.content = b"".join([fragment async for fragment in handle.open()])
        return _parsed("internal")


@pytest.mark.asyncio
async def test_path_only_parser_gets_materialized_path_and_public_identity(
    tmp_path: Path,
    runner: BoundedBlockingRunner,
    caplog: pytest.LogCaptureFixture,
) -> None:
    artifact = tmp_path / "report.txt"
    artifact.write_text("contents", encoding="utf-8")
    materialized: list[int] = []
    cleaned: list[int] = []
    parser = PathParser()

    with caplog.at_level(logging.INFO):
        result = await ParserInputAdapter(runner).parse(
            parser, _handle(artifact, materialized=materialized, cleaned=cleaned)
        )

    assert parser.inputs == [str(artifact)]
    assert result.source == "https://example.org/report.txt"
    assert materialized == [1]
    assert cleaned == [1]
    assert "source.materialize.completed" in caplog.messages
    assert str(artifact) not in caplog.text


@pytest.mark.asyncio
async def test_handle_aware_parser_streams_without_materializing(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    artifact = tmp_path / "report.txt"
    artifact.write_bytes(b"streamed")
    materialized: list[int] = []
    cleaned: list[int] = []
    parser = HandleParser()

    result = await ParserInputAdapter(runner).parse(
        parser, _handle(artifact, materialized=materialized, cleaned=cleaned)
    )

    assert parser.content == b"streamed"
    assert result.source == "https://example.org/report.txt"
    assert materialized == []
    assert cleaned == [1]


@pytest.mark.asyncio
async def test_unchanged_sync_third_party_parser_receives_string_path(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    artifact = tmp_path / "report.txt"
    artifact.write_text("content", encoding="utf-8")
    seen: list[str] = []

    class SyncParser:
        def parse(self, source: str) -> ParsedDocument:
            seen.append(source)
            return _parsed(source)

    await ParserInputAdapter(runner).parse(
        SyncParser(), _handle(artifact, materialized=[], cleaned=[])
    )
    assert seen == [str(artifact)]


@pytest.mark.asyncio
async def test_failure_and_cancellation_both_cleanup_handle(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    artifact = tmp_path / "report.txt"
    artifact.write_text("content", encoding="utf-8")
    failed_cleanup: list[int] = []

    class FailingParser:
        async def aparse(self, source: str) -> ParsedDocument:
            raise ValueError(f"parser failed for {source}")

    with pytest.raises(ParseError, match="resolved source") as failure:
        await ParserInputAdapter(runner).parse(
            FailingParser(), _handle(artifact, materialized=[], cleaned=failed_cleanup)
        )
    assert str(artifact) not in str(failure.value)
    assert failed_cleanup == [1]

    started = asyncio.Event()
    cancelled_cleanup: list[int] = []

    class WaitingParser:
        async def aparse(self, source: str) -> ParsedDocument:
            started.set()
            await asyncio.Event().wait()
            return _parsed(source)

    task = asyncio.create_task(
        ParserInputAdapter(runner).parse(
            WaitingParser(), _handle(artifact, materialized=[], cleaned=cancelled_cleanup)
        )
    )
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled_cleanup == [1]
