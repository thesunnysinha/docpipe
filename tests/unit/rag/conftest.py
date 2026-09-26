"""Managed blocking runner fixture for RAG component tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from docpipe.core.blocking import BoundedBlockingRunner


@pytest.fixture
async def active_runner() -> AsyncIterator[BoundedBlockingRunner]:
    async with BoundedBlockingRunner(max_concurrency=2) as runner:
        yield runner
