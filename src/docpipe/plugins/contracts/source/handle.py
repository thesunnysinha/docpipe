"""Asynchronous source content handle with explicit cleanup ownership."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from docpipe.plugins.contracts.source.models import SourceDescriptor

StreamFactory = Callable[[], AsyncIterator[bytes]]
MaterializeFactory = Callable[[], Awaitable[Path]]
Cleanup = Callable[[], Awaitable[None]]


@runtime_checkable
class ResolvedSourceHandle(Protocol):
    """Open and materialize bytes only during the owned context lifetime."""

    @property
    def descriptor(self) -> SourceDescriptor:
        """Return immutable resolved-source metadata."""
        ...

    async def __aenter__(self) -> ResolvedSourceHandle:
        """Enter exclusive ownership of this handle."""
        ...

    async def __aexit__(self, *exc_info: object) -> None:
        """Release owned resources, including after cancellation."""
        ...

    def open(self) -> AsyncIterator[bytes]:
        """Stream content in bounded byte fragments while active."""
        ...

    async def materialize(self) -> Path:
        """Return a lifecycle-bound readable local artifact."""
        ...

    async def aclose(self) -> None:
        """Idempotently release owned resources."""
        ...


class ManagedSourceHandle:
    """One-shot managed source handle with exactly-once asynchronous cleanup."""

    def __init__(
        self,
        descriptor: SourceDescriptor,
        *,
        stream_factory: StreamFactory,
        materialize_factory: MaterializeFactory,
        cleanup: Cleanup,
    ) -> None:
        self.descriptor = descriptor
        self._stream_factory = stream_factory
        self._materialize_factory = materialize_factory
        self._cleanup = cleanup
        self._active = False
        self._closed = False
        self._close_lock = asyncio.Lock()

    async def __aenter__(self) -> ManagedSourceHandle:
        """Activate this one-shot handle or reject reuse after release."""
        if self._active or self._closed:
            raise RuntimeError("source handle is already active or closed")
        self._active = True
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close on normal exit, error, and task cancellation."""
        await self.aclose()

    def open(self) -> AsyncIterator[bytes]:
        """Return a stream checked at creation and on every byte fragment."""
        self._require_active()

        async def checked_stream() -> AsyncIterator[bytes]:
            async for fragment in self._stream_factory():
                self._require_active()
                if not isinstance(fragment, bytes):
                    raise TypeError("source stream fragments must be bytes")
                yield fragment

        return checked_stream()

    async def materialize(self) -> Path:
        """Materialize while active without exposing an unowned path."""
        self._require_active()
        result = await self._materialize_factory()
        self._require_active()
        return result

    async def aclose(self) -> None:
        """Run the cleanup callback exactly once, even across repeated calls."""
        async with self._close_lock:
            if self._closed:
                return
            self._active = False
            self._closed = True
            await self._cleanup()

    def _require_active(self) -> None:
        if not self._active or self._closed:
            raise RuntimeError("source handle is not active")
