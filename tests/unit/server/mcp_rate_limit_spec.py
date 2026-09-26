"""Pre-auth rate-limit coverage for the mounted MCP endpoint."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import Response

from docpipe.config.settings import DocpipeSettings
from docpipe.server.rate_limit import PresetRateLimitMiddleware


def test_mcp_post_uses_operator_configured_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = DocpipeSettings(mcp_rate_limit_per_minute=42)
    app = SimpleNamespace(state=SimpleNamespace(docpipe_runtime=SimpleNamespace(settings=settings)))
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [],
            "client": ("127.0.0.1", 50000),
            "app": app,
        }
    )
    observed: dict[str, object] = {}

    def check_limit(key: str, limit: int) -> None:
        observed["key"] = key
        observed["limit"] = limit
        return None

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    monkeypatch.setattr("docpipe.server.rate_limit._check_limit", check_limit)
    response = asyncio.run(PresetRateLimitMiddleware(app).dispatch(request, call_next))

    assert response.status_code == 200
    assert observed["key"] == "127.0.0.1:/mcp"
    assert observed["limit"] == 42


def test_mcp_post_uses_forwarded_address_only_for_configured_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = DocpipeSettings(
        mcp_rate_limit_per_minute=42,
        rate_limit_trusted_proxy_cidrs=("10.0.0.0/8",),
    )
    app = SimpleNamespace(state=SimpleNamespace(docpipe_runtime=SimpleNamespace(settings=settings)))
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp/",
            "headers": [(b"x-forwarded-for", b"198.51.100.23")],
            "client": ("10.0.0.8", 50000),
            "app": app,
        }
    )
    observed: dict[str, object] = {}

    def check_limit(key: str, limit: int) -> None:
        observed["key"] = key
        observed["limit"] = limit
        return None

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    monkeypatch.setattr("docpipe.server.rate_limit._check_limit", check_limit)
    response = asyncio.run(PresetRateLimitMiddleware(app).dispatch(request, call_next))

    assert response.status_code == 200
    assert observed["key"] == "198.51.100.23:/mcp/"
    assert observed["limit"] == 42


def test_trusted_proxy_cidr_setting_rejects_invalid_network() -> None:
    with pytest.raises(ValueError, match="valid IP CIDRs"):
        DocpipeSettings(rate_limit_trusted_proxy_cidrs=("not-a-network",))
