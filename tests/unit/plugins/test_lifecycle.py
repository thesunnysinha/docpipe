"""Tests for process, request, and operation plugin lifecycles."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

import pytest

from docpipe.plugins.lifecycle import PluginRuntime, PluginScope


@pytest.mark.asyncio
async def test_scopes_reuse_instances_and_close_exactly_once() -> None:
    created: list[str] = []
    closed: list[str] = []

    @asynccontextmanager
    async def resource(name: str) -> AsyncIterator[object]:
        created.append(name)
        try:
            yield object()
        finally:
            closed.append(name)

    async with PluginRuntime() as runtime:
        process_one = await runtime.acquire("client", lambda: resource("process"))
        process_two = await runtime.acquire("client", lambda: resource("ignored"))
        assert process_one is process_two

        async with runtime.request_scope() as request:
            request_one = await request.acquire("client", lambda: resource("request"))
            request_two = await request.acquire("client", lambda: resource("ignored"))
            assert request_one is request_two
            async with request.operation_scope() as operation:
                operation_value = await operation.acquire("client", lambda: resource("operation"))
                request_from_operation = await operation.acquire(
                    "client", lambda: resource("ignored"), scope=PluginScope.REQUEST
                )
                assert request_from_operation is request_one
                assert operation_value is not request_one
            assert closed == ["operation"]
        assert closed == ["operation", "request"]
    assert closed == ["operation", "request", "process"]
    assert created == ["process", "request", "operation"]


@pytest.mark.asyncio
async def test_runtime_supports_sync_context_managers() -> None:
    closed = 0

    @contextmanager
    def resource() -> Iterator[object]:
        nonlocal closed
        try:
            yield object()
        finally:
            closed += 1

    async with PluginRuntime() as runtime:
        await runtime.acquire("sync", resource)

    assert closed == 1


@pytest.mark.asyncio
async def test_partial_construction_failure_still_closes_prior_resources() -> None:
    closed = 0

    @asynccontextmanager
    async def valid() -> AsyncIterator[object]:
        nonlocal closed
        try:
            yield object()
        finally:
            closed += 1

    def broken() -> object:
        raise RuntimeError("construction failed")

    with pytest.raises(RuntimeError, match="construction failed"):
        async with PluginRuntime() as runtime:
            await runtime.acquire("valid", valid)
            await runtime.acquire("broken", broken)

    assert closed == 1


@pytest.mark.asyncio
async def test_cancelled_scope_closes_resources_once() -> None:
    closed = 0

    @asynccontextmanager
    async def resource() -> AsyncIterator[object]:
        nonlocal closed
        try:
            yield object()
        finally:
            closed += 1

    async with PluginRuntime() as runtime:
        with pytest.raises(asyncio.CancelledError):
            async with runtime.request_scope() as request:
                await request.acquire("resource", resource)
                raise asyncio.CancelledError

    assert closed == 1
