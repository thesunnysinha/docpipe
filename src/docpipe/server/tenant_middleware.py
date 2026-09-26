"""Bind tenant policy context only to verified application credentials."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from docpipe.config.settings import DocpipeSettings
from docpipe.profiles.guardrails import reset_tenant_context, set_tenant_context

_PUBLIC_HEALTH_PATHS = frozenset({"/health", "/health/live", "/health/ready"})


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Resolve an authenticated username through an operator-owned tenant map.

    A caller-supplied tenant header is intentionally ignored. If tenant policies
    are configured, a valid credential must map to a configured tenant or the
    request is rejected before application operations can run.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings: DocpipeSettings = request.app.state.docpipe_runtime.settings
        tenant_id: str | None = None
        if settings.tenant_plugin_policies and request.url.path not in _PUBLIC_HEALTH_PATHS:
            username, password = _basic_credentials(request)
            if username is None or password is None:
                # Let the normal auth dependency produce its standard 401.
                return await call_next(request)

            from docpipe.server.auth import verify_credentials

            if not settings.auth_enabled or not verify_credentials(
                username, password, settings=settings
            ):
                # Again, leave invalid credentials to the auth dependency.
                return await call_next(request)

            tenant_id = settings.tenant_identity_map.get(username)
            configured_tenants = _configured_tenants(settings.tenant_plugin_policies)
            if tenant_id is None or tenant_id not in configured_tenants:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Authenticated user has no configured tenant policy."},
                )

        token = set_tenant_context(tenant_id, settings=settings)
        try:
            return await call_next(request)
        finally:
            reset_tenant_context(token)


def _basic_credentials(request: Request) -> tuple[str | None, str | None]:
    """Decode a Basic credential without accepting malformed encodings."""
    scheme, separator, value = request.headers.get("Authorization", "").partition(" ")
    if not separator or scheme.casefold() != "basic":
        return None, None
    try:
        decoded = base64.b64decode(value.strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None, None
    username, separator, password = decoded.partition(":")
    return (username, password) if separator else (None, None)


def _configured_tenants(raw_policies: str) -> set[str]:
    """Return policy tenant names, failing closed for malformed configuration."""
    try:
        policies = json.loads(raw_policies)
    except json.JSONDecodeError:
        return set()
    if not isinstance(policies, dict):
        return set()
    return {
        tenant
        for tenant, policy in policies.items()
        if isinstance(tenant, str) and isinstance(policy, dict)
    }
