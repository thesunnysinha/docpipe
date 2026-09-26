"""Tenant identity propagation tests for per-tenant cache key isolation."""

from __future__ import annotations

import base64
import sys
from types import SimpleNamespace

from starlette.requests import Request
from starlette.responses import Response

from docpipe.config.settings import DocpipeSettings
from docpipe.profiles.guardrails import get_tenant_context
from docpipe.server.tenant_middleware import TenantContextMiddleware


async def test_authenticated_identity_map_binds_tenant_without_plugin_policy(monkeypatch) -> None:
    settings = DocpipeSettings(
        auth_enabled=True,
        username="alice",
        password="test-password",
        tenant_identity_map={"alice": "tenant-finance"},
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/rag/query",
            "headers": [
                (
                    b"authorization",
                    b"Basic " + base64.b64encode(b"alice:test-password"),
                )
            ],
            "app": SimpleNamespace(
                state=SimpleNamespace(docpipe_runtime=SimpleNamespace(settings=settings))
            ),
        }
    )
    seen_tenant: str | None = None

    async def call_next(_request: Request) -> Response:
        nonlocal seen_tenant
        seen_tenant = get_tenant_context()
        return Response(status_code=204)

    middleware = TenantContextMiddleware(SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "docpipe.server.auth",
        SimpleNamespace(verify_credentials=lambda username, password, *, settings: True),
    )
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 204
    assert seen_tenant == "tenant-finance"
    assert get_tenant_context() is None
