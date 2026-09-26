"""URL policy and connection-time DNS pinning against SSRF and rebinding."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from docpipe.plugins.errors import UnsafeSourceError
from docpipe.sources.http_security import (
    HttpSecurityPolicy,
    PinnedNetworkBackend,
    inspect_http_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/secrets",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/secrets",
        "http://user:secret@example.org/report",
        "file:///tmp/report.pdf",
        "http://example.org:9/report",
    ],
)
def test_url_validation_blocks_unsafe_targets_and_credentials(url: str) -> None:
    with pytest.raises(UnsafeSourceError):
        inspect_http_url(url, HttpSecurityPolicy(allow_private=False))


@pytest.mark.asyncio
async def test_connection_resolves_once_and_connects_only_to_vetted_ip() -> None:
    backend = AsyncMock()
    addresses = iter(("8.8.8.8", "127.0.0.1"))

    async def resolve(host: str, port: int) -> tuple[str, ...]:
        return (next(addresses),)

    pinned = PinnedNetworkBackend(
        backend, HttpSecurityPolicy(allow_private=False), resolve_host=resolve
    )
    await pinned.connect_tcp("example.org", 443, timeout=3)

    assert backend.connect_tcp.await_args.args[:2] == ("8.8.8.8", 443)
    # A second resolution is deliberately unsafe and is never passed to TCP.
    with pytest.raises(UnsafeSourceError):
        await pinned.connect_tcp("example.org", 443, timeout=3)
    assert backend.connect_tcp.await_count == 1


@pytest.mark.asyncio
async def test_connect_rejects_mixed_public_and_private_answers() -> None:
    backend = AsyncMock()

    async def resolve(host: str, port: int) -> tuple[str, ...]:
        return ("8.8.8.8", "10.0.0.1")

    pinned = PinnedNetworkBackend(
        backend, HttpSecurityPolicy(allow_private=False), resolve_host=resolve
    )
    with pytest.raises(UnsafeSourceError):
        await pinned.connect_tcp("example.org", 80)
    backend.connect_tcp.assert_not_awaited()
