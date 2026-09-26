"""Bounded execution for synchronous adapter operations."""

from __future__ import annotations

import asyncio
import contextvars
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TypeVar, overload

from docpipe.core.operation import OperationContext, OperationDeadlineExceededError

_LOGGER = logging.getLogger(__name__)
Result = TypeVar("Result")
Argument = TypeVar("Argument")
SecondArgument = TypeVar("SecondArgument")


class BoundedBlockingRunner:
    """Run blocking calls in a private executor with bounded concurrency.

    Cancelling an await cannot terminate Python code already running in a thread.
    The runner limits those threads and discards late results after cancellation.
    """

    def __init__(self, max_concurrency: int, *, logger: logging.Logger | None = None) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least one")
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrency,
            thread_name_prefix="docpipe-blocking",
        )
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._logger = logger or _LOGGER
        self._closed = False

    async def __aenter__(self) -> BoundedBlockingRunner:
        """Enter the runner lifecycle."""
        if self._closed:
            raise RuntimeError("blocking runner is closed")
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Cancel queued futures and release executor resources."""
        self.close()

    @overload
    async def run(
        self,
        function: Callable[[], Result],
        /,
        *,
        context: OperationContext | None = None,
    ) -> Result: ...

    @overload
    async def run(
        self,
        function: Callable[[Argument], Result],
        argument: Argument,
        /,
        *,
        context: OperationContext | None = None,
    ) -> Result: ...

    @overload
    async def run(
        self,
        function: Callable[[Argument, SecondArgument], Result],
        argument: Argument,
        second_argument: SecondArgument,
        /,
        *,
        context: OperationContext | None = None,
    ) -> Result: ...

    async def run(
        self,
        function: Callable[..., object],
        *arguments: object,
        context: OperationContext | None = None,
    ) -> object:
        """Run a blocking callable within the concurrency and deadline bounds."""
        if self._closed:
            raise RuntimeError("blocking runner is closed")
        if context is not None:
            context.ensure_active()
        call = partial(function, *arguments)
        operation = self._run_bounded(call)
        timeout = context.remaining_seconds() if context is not None else None
        request_id = context.request_id if context is not None else "unknown"
        if timeout is None:
            return await operation
        try:
            return await asyncio.wait_for(operation, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._logger.warning(
                "operation.deadline.exceeded",
                extra={
                    "event": "operation.deadline.exceeded",
                    "request_id": request_id,
                },
            )
            raise OperationDeadlineExceededError(
                "operation deadline exceeded",
                context={"request_id": request_id},
            ) from exc

    async def _run_bounded(self, function: Callable[[], object]) -> object:
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            copied_context = contextvars.copy_context()
            return await loop.run_in_executor(self._executor, copied_context.run, function)

    def close(self) -> None:
        """Reject new work and cancel futures that have not started."""
        if self._closed:
            return
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
