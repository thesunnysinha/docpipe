"""HTTP deadlines, cancellation, and secret-free diagnostics."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
import pytest

from docpipe.plugins.errors import SourceAccessError
from tests.unit.sources.http.support import WaitingStream, client_for, resolver_for


@pytest.mark.asyncio
async def should_redact_signed_urls_from_logs_and_errors(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    async with client_for(lambda request: httpx.Response(503)) as client:
        with caplog.at_level(logging.INFO), pytest.raises(Exception) as failure:
            await resolver_for(tmp_path, client).resolve(
                "https://example.org/doc?X-Amz-Signature=very-private"
            )
        assert "very-private" not in caplog.text
        assert "very-private" not in str(failure.value)


@pytest.mark.asyncio
async def should_remove_partial_download_after_cancellation(tmp_path: Path) -> None:
    started = asyncio.Event()
    async with client_for(
        lambda request: httpx.Response(200, stream=WaitingStream(started), request=request)
    ) as client:
        task = asyncio.create_task(
            resolver_for(tmp_path, client, total_timeout=10).resolve(
                "https://example.org/report.txt"
            )
        )
        await asyncio.wait_for(started.wait(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def should_report_timeout_safely_and_remove_partial_download(tmp_path: Path) -> None:
    started = asyncio.Event()
    async with client_for(
        lambda request: httpx.Response(200, stream=WaitingStream(started), request=request)
    ) as client:
        with pytest.raises(SourceAccessError, match="deadline"):
            await resolver_for(tmp_path, client, total_timeout=0.01).resolve(
                "https://example.org/report.txt?signature=private"
            )
        assert list(tmp_path.iterdir()) == []
