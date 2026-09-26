"""HTTP redirects stay inside vetted transport and host policy."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from docpipe.plugins.errors import UnsafeSourceError
from tests.unit.sources.http.support import client_for, resolver_for


@pytest.mark.asyncio
async def should_reject_private_redirect_before_request(tmp_path: Path) -> None:
    destinations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        destinations.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secrets"})

    async with client_for(handler) as client:
        with pytest.raises(UnsafeSourceError):
            await resolver_for(tmp_path, client).resolve("https://example.org/doc.txt")
    assert destinations == ["https://example.org/doc.txt"]


@pytest.mark.asyncio
async def should_reject_https_downgrade(tmp_path: Path) -> None:
    destinations: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        destinations.append(str(request.url))
        return httpx.Response(
            302, headers={"location": "http://example.org/insecure"}, request=request
        )

    async with client_for(handler) as client:
        with pytest.raises(UnsafeSourceError, match="downgrade"):
            await resolver_for(tmp_path, client).resolve("https://example.org/doc.txt")
    assert destinations == ["https://example.org/doc.txt"]


@pytest.mark.asyncio
async def should_stop_at_redirect_limit_without_extra_request(tmp_path: Path) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "/next"}, request=request)

    async with client_for(handler) as client:
        with pytest.raises(UnsafeSourceError, match="redirect limit"):
            await resolver_for(tmp_path, client, max_redirects=0).resolve(
                "https://example.org/doc.txt"
            )
    assert requests == ["https://example.org/doc.txt"]
