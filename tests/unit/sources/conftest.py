"""Owned blocking runner for isolated local-source tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from docpipe.core.blocking import BoundedBlockingRunner


@pytest.fixture
async def runner() -> AsyncIterator[BoundedBlockingRunner]:
    async with BoundedBlockingRunner(max_concurrency=2) as bounded:
        yield bounded
