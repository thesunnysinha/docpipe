"""Tests for bounded vendor-neutral ingestion orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from tests.unit.ingestion.coordinator_support import (
    AdminDouble,
    BuilderDouble,
    ChunkerDouble,
    EncoderDouble,
    WriterDouble,
    parsed_document,
)

from docpipe.ingestion.configuration import IngestionOptions
from docpipe.ingestion.coordinator import IncompleteIngestionError, IngestionCoordinator
from docpipe.plugins.contracts.vectorstore import CollectionRef


@pytest.mark.asyncio
async def should_sequence_and_bound_batches() -> None:
    events: list[str] = []
    writer = WriterDouble(events)
    coordinator = IngestionCoordinator(
        options=IngestionOptions(
            collection=CollectionRef("documents"),
            batch_size=2,
            max_in_flight=2,
        ),
        builder=BuilderDouble(5),
        chunker=ChunkerDouble(events),
        encoder=EncoderDouble(events),
        writer=writer,
        admin=AdminDouble(events),
    )

    result = await coordinator.ingest(parsed_document())

    assert result.chunks_ingested == 5
    assert sorted(writer.batch_sizes) == [1, 2, 2]
    assert writer.maximum_active <= 2
    assert events.index("chunk") < events.index("encode:2")
    assert events.index("ensure:8") < events.index("write:2")


@pytest.mark.asyncio
@pytest.mark.parametrize(("rejected", "uncertain"), [(1, 0), (0, 1)])
async def should_never_report_incomplete_write_as_success(
    rejected: int,
    uncertain: int,
) -> None:
    events: list[str] = []
    coordinator = IngestionCoordinator(
        options=IngestionOptions(collection=CollectionRef("documents")),
        builder=BuilderDouble(1),
        chunker=ChunkerDouble(events),
        encoder=EncoderDouble(events),
        writer=WriterDouble(events, rejected=rejected, uncertain=uncertain),
        admin=AdminDouble(events),
    )

    with pytest.raises(IncompleteIngestionError) as caught:
        await coordinator.ingest(parsed_document())

    assert caught.value.accepted == 0
    assert caught.value.rejected == rejected
    assert caught.value.uncertain == uncertain


@pytest.mark.asyncio
async def should_close_operation_resources_on_cancellation() -> None:
    events: list[str] = []
    release = asyncio.Event()
    chunker = ChunkerDouble(events, release)
    closed = 0

    @asynccontextmanager
    async def operation_scope() -> AsyncIterator[object]:
        nonlocal closed
        try:
            yield object()
        finally:
            closed += 1

    coordinator = IngestionCoordinator(
        options=IngestionOptions(collection=CollectionRef("documents")),
        builder=BuilderDouble(1),
        chunker=chunker,
        encoder=EncoderDouble(events),
        writer=WriterDouble(events),
        admin=AdminDouble(events),
        operation_scope_factory=operation_scope,
    )

    task = asyncio.create_task(coordinator.ingest(parsed_document()))
    await chunker.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert closed == 1
