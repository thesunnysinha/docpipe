"""Managed source handle lifetime and idempotent cleanup."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from docpipe.plugins.contracts.source import SourceDescriptor
from docpipe.plugins.contracts.source.handle import ManagedSourceHandle


def _handle(tmp_path: Path, closed: list[int]) -> ManagedSourceHandle:
    async def stream() -> AsyncIterator[bytes]:
        yield b"one"
        yield b"two"

    async def materialize() -> Path:
        return tmp_path / "report.pdf"

    async def cleanup() -> None:
        closed.append(1)

    return ManagedSourceHandle(
        SourceDescriptor("file:///report.pdf", "report.pdf"),
        stream_factory=stream,
        materialize_factory=materialize,
        cleanup=cleanup,
    )


@pytest.mark.asyncio
async def test_context_only_open_and_materialize_then_cleanup_exactly_once(tmp_path: Path) -> None:
    closed: list[int] = []
    handle = _handle(tmp_path, closed)
    with pytest.raises(RuntimeError, match="active"):
        await handle.materialize()
    async with handle:
        assert [part async for part in handle.open()] == [b"one", b"two"]
        assert await handle.materialize() == tmp_path / "report.pdf"
    assert closed == [1]
    await handle.aclose()
    assert closed == [1]
    with pytest.raises(RuntimeError, match="active"):
        await handle.materialize()
    with pytest.raises(RuntimeError, match="active"):
        _ = [part async for part in handle.open()]


@pytest.mark.asyncio
async def test_exception_and_cancelled_operation_both_release_handle(tmp_path: Path) -> None:
    closed: list[int] = []
    handle = _handle(tmp_path, closed)
    with pytest.raises(ValueError):
        async with handle:
            raise ValueError("private content")
    assert closed == [1]

    cancelled: list[int] = []
    second = _handle(tmp_path, cancelled)

    async def wait_inside() -> None:
        async with second:
            await asyncio.Event().wait()

    task = asyncio.create_task(wait_inside())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled == [1]
