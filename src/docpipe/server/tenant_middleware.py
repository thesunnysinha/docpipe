"""Bind per-request tenant context for plugin policy overrides."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from docpipe.profiles.guardrails import reset_tenant_context, set_tenant_context


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        tenant = request.headers.get("X-Docpipe-Tenant-Id")
        token = set_tenant_context(tenant)
        try:
            return await call_next(request)
        finally:
            reset_tenant_context(token)
