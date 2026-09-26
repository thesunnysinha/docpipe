"""Compatibility bridge from resolved source handles to parser input shapes."""

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
    """Optional parser extension that consumes an active source handle."""

    async def aparse_source(self, handle: ResolvedSourceHandle) -> ParsedDocument:
        """Parse directly from a stream-capable source handle."""
        ...


@runtime_checkable
class AsyncPathParser(Protocol):
    """Existing asynchronous parser interface receiving a local path string."""

    async def aparse(self, source: str) -> ParsedDocument:
        """Parse one local source path."""
        ...


@runtime_checkable
class SyncPathParser(Protocol):
    """Existing synchronous parser interface receiving a local path string."""

    def parse(self, source: str) -> ParsedDocument:
        """Parse one local source path."""
        ...


class ParserInputAdapter:
    """Own handle lifetime while preserving unchanged parser call shapes."""

    def __init__(self, blocking_runner: BoundedBlockingRunner) -> None:
        self._blocking_runner = blocking_runner

    async def parse(self, parser: object, handle: ResolvedSourceHandle) -> ParsedDocument:
        """Parse through the richest supported input without leaking artifacts."""
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
