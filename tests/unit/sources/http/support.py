"""Small HTTP transport fixtures shared by source behavior specs."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import httpx

from docpipe.sources.http import HttpSourceConfig, HttpSourceResolver
from docpipe.sources.http_security import HttpSecurityPolicy


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    """Wrap a deterministic handler without environmental transport access."""
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False
    )


def resolver_for(root: Path, client: httpx.AsyncClient, **options: object) -> HttpSourceResolver:
    """Create a public-network-only resolver for a private test root."""
    return HttpSourceResolver(
        HttpSourceConfig(temporary_root=root, **options),
        client=client,
        security=HttpSecurityPolicy(allow_private=False),
    )


class WaitingStream(httpx.AsyncByteStream):
    """Yield one fragment, then wait until cancelled or timed out."""

    def __init__(self, started: asyncio.Event) -> None:
        self._started = started

    async def __aiter__(self):
        """Keep a download in flight after the first fragment."""
        yield b"partial"
        self._started.set()
        await asyncio.Event().wait()
