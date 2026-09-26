"""Adapt resolved source handles to the input shape expected by a parser.

The adapter owns the handle context for the full parse operation. It prefers a
handle-aware streaming parser; otherwise it materializes the source and calls
an async path parser or runs a sync path parser through the bounded executor.
The returned document always receives the handle's public source identifier,
and ordinary parser failures are exposed as a sanitized :class:`ParseError`.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.core.errors import ParseError
from docpipe.core.types import ParsedDocument
from docpipe.plugins.contracts.source import ResolvedSourceHandle

_LOGGER = logging.getLogger(__name__)


@runtime_checkable
class HandleAwareParser(Protocol):
    """Optional parser interface for consuming an active source handle.

    Implementations may stream bounded bytes or materialize a lifecycle-bound
    path through the handle. They must finish using it before returning because
    the adapter closes the handle as soon as parsing completes or fails.
    """

    async def aparse_source(self, handle: ResolvedSourceHandle) -> ParsedDocument:
        """Parse one resolved source while its handle context is active.

        Args:
            handle: Active handle owned by :class:`ParserInputAdapter`.

        Returns:
            Parsed document; the adapter replaces its ``source`` field with
            the handle's public source identifier before returning.

        Raises:
            Exception: Implementation failures are wrapped in :class:`ParseError`
                by the adapter, while task cancellation propagates unchanged.
        """
        ...


@runtime_checkable
class AsyncPathParser(Protocol):
    """Asynchronous compatibility interface receiving a materialized path."""

    async def aparse(self, source: str) -> ParsedDocument:
        """Parse one document from the local path supplied by the adapter.

        The argument is a path string, not the original URL/source identifier.
        The adapter owns and closes the source handle around this call.
        """
        ...


@runtime_checkable
class SyncPathParser(Protocol):
    """Synchronous compatibility interface receiving a materialized path."""

    def parse(self, source: str) -> ParsedDocument:
        """Parse one document from the local path supplied by the adapter.

        The adapter runs this blocking method through its bounded executor and
        closes the source handle after it returns or raises.
        """
        ...


class ParserInputAdapter:
    """Own source-handle lifetime while preserving legacy parser call shapes.

    Parser preference is structural: handle-aware async parsing first, then
    async path parsing, then sync path parsing. The latter two receive a
    materialized local path; synchronous parsing is offloaded to the injected
    bounded runner. Parser exceptions are wrapped to avoid returning raw
    provider messages that may include sensitive input details.
    """

    def __init__(self, blocking_runner: BoundedBlockingRunner) -> None:
        """Create an adapter using the runtime's bounded blocking executor.

        Args:
            blocking_runner: Executor used only for synchronous parser calls.
                Its lifecycle remains owned by the runtime, not this adapter.
        """
        self._blocking_runner = blocking_runner

    async def parse(self, parser: object, handle: ResolvedSourceHandle) -> ParsedDocument:
        """Parse a resolved source using the richest parser interface available.

        Selection order is ``aparse_source(handle)``, ``aparse(path)``, then
        ``parse(path)``. A parser that implements none of these protocols is
        rejected. The source handle remains active throughout parsing and is
        closed on success, parser failure, or cancellation. The final document
        source is normalized to the handle's public source identifier.

        Args:
            parser: Object implementing one of the supported parser protocols.
            handle: Resolved source handle whose context this method owns.

        Returns:
            Parsed document with ``source`` set to ``handle.descriptor.source_id``.

        Raises:
            ParseError: If materialization, parser-interface selection, or
                parsing raises an ordinary exception. The underlying exception
                is retained as the cause, while its message is not copied into
                the public error text.
            asyncio.CancelledError: Cancellation propagates unchanged after
                handle cleanup.
        """
        async with handle:
            try:
                if isinstance(parser, HandleAwareParser):
                    parsed = await parser.aparse_source(handle)
                else:
                    started = time.monotonic()
                    artifact = await handle.materialize()
                    source_id = handle.descriptor.source_id
                    _LOGGER.info(
                        "source.materialize.completed",
                        extra={
                            "event": "source.materialize.completed",
                            "source_scheme": urlsplit(source_id).scheme or "file",
                            "source_key": hashlib.blake2b(
                                source_id.encode("utf-8"), digest_size=12
                            ).hexdigest(),
                            "duration_ms": round((time.monotonic() - started) * 1000, 3),
                        },
                    )
                    source = str(artifact)
                    if isinstance(parser, AsyncPathParser):
                        parsed = await parser.aparse(source)
                    elif isinstance(parser, SyncPathParser):
                        parsed = await self._blocking_runner.run(parser.parse, source)
                    else:
                        raise TypeError("parser must implement a supported parse interface")
            except Exception as error:
                raise ParseError("Failed to parse resolved source") from error
            return parsed.model_copy(update={"source": handle.descriptor.source_id})
