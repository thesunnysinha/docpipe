"""Tests for bounded execution of blocking adapter calls."""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.core.operation import OperationContext, OperationDeadlineExceededError


@pytest.mark.asyncio
async def test_blocking_runner_never_exceeds_configured_concurrency() -> None:
    active = 0
    maximum = 0
    lock = threading.Lock()

    def work(value: int) -> int:
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return value

    async with BoundedBlockingRunner(max_concurrency=2) as runner:
        results = await asyncio.gather(*(runner.run(work, value) for value in range(6)))

    assert results == list(range(6))
    assert maximum == 2


@pytest.mark.asyncio
async def test_expired_deadline_does_not_start_blocking_work() -> None:
    called = False

    def work() -> None:
        nonlocal called
        called = True

    context = OperationContext(
        request_id="req-1",
        deadline=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    async with BoundedBlockingRunner(max_concurrency=1) as runner:
        with pytest.raises(OperationDeadlineExceededError):
            await runner.run(work, context=context)

    assert not called


@pytest.mark.asyncio
async def test_running_thread_is_bounded_and_late_result_is_discarded_on_cancel() -> None:
    started = threading.Event()
    release = threading.Event()

    def work() -> str:
        started.set()
        release.wait(timeout=1)
        return "late"

    async with BoundedBlockingRunner(max_concurrency=1) as runner:
        task = asyncio.create_task(runner.run(work))
        while not started.is_set():
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
