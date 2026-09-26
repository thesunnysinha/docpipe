"""Construct the FastAPI application and compose optional hosted MCP support."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI

from docpipe._version import __version__
from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.bootstrap.server import create_server_lifespan, create_server_runtime
from docpipe.config.loader import load_config
from docpipe.config.settings import DocpipeSettings
from docpipe.server.bootstrap import (
    configure_app_runtime,
    register_exception_handlers,
)
from docpipe.server.routers import register_routers
from docpipe.server.services.documents import DocumentService
from docpipe.server.services.rag import RAGService


def create_app(settings: DocpipeSettings | None = None) -> FastAPI:
    """Create the API app with runtime, lifespan, middleware, handlers, and routes.

    When settings are omitted, configuration is loaded from the normal
    application sources. Hosted MCP is mounted only when enabled and requires
    the optional server dependency; its lifespan is combined with the API's.
    """
    resolved_settings = settings or load_config()
    runtime = create_server_runtime(resolved_settings)
    lifespan = create_server_lifespan(runtime)
    app = FastAPI(
        title="docpipe",
        description="Unified document parsing, extraction, and RAG ingestion API.",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.docpipe_runtime = runtime
    configure_app_runtime(app, resolved_settings)
    register_exception_handlers(app)
    register_routers(app)
    if resolved_settings.mcp_server_enabled:
        mcp_app = _create_mcp_app(app, runtime, resolved_settings)
        try:
            from fastmcp.utilities.lifespan import combine_lifespans
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "Hosted MCP support requires the optional 'mcp-server' dependency."
            ) from exc
        app.router.lifespan_context = combine_lifespans(lifespan, mcp_app.lifespan)
        app.mount("/mcp", mcp_app)
    return app


def _create_mcp_app(app: FastAPI, runtime: DocpipeRuntime, settings: DocpipeSettings) -> Any:
    """Build the optional hosted MCP app using application runtime services.

    Operator tokens and host/origin restrictions are passed from settings.
    The configured MCP tenant is a shared deployment scope, not an identity
    independently derived from each bearer token.
    """
    from docpipe.mcp_server import create_mcp_asgi_app

    _validate_mcp_tenant_scope(settings)

    rag_service = RAGService(
        settings,
        runtime,
        cache_backend_provider=lambda: getattr(app.state, "rag_cache", None),
    )
    document_service = DocumentService(settings, runtime.legacy_registry, runtime)
    return create_mcp_asgi_app(
        document_service,
        rag_service,
        settings,
        operator_tokens=tuple(token.get_secret_value() for token in settings.mcp_operator_tokens),
        allowed_hosts=settings.mcp_allowed_hosts,
        allowed_origins=settings.mcp_allowed_origins,
        endpoint_path="/",
        tool_timeout_seconds=settings.mcp_tool_timeout_seconds,
        tenant_id=settings.mcp_tenant_id,
    )


def _validate_mcp_tenant_scope(settings: DocpipeSettings) -> None:
    """Require a valid configured MCP tenant when tenant policy is enabled.

    If tenant identity or plugin policies are configured, startup fails unless
    ``mcp_tenant_id`` is present and belongs to the configured policy/identity
    mapping. With no tenant-scoped policy, this check does not require a tenant.
    """
    tenant_scoped = bool(settings.tenant_identity_map or settings.tenant_plugin_policies)
    if tenant_scoped and not settings.mcp_tenant_id:
        raise ValueError(
            "MCP bearer clients require DOCPIPE_MCP_TENANT_ID when tenant identity or "
            "plugin policies are configured."
        )
    if settings.tenant_plugin_policies:
        try:
            tenant_policies = json.loads(settings.tenant_plugin_policies)
        except json.JSONDecodeError as exc:
            raise ValueError("DOCPIPE_TENANT_PLUGIN_POLICIES must contain valid JSON.") from exc
        if not isinstance(tenant_policies, dict) or settings.mcp_tenant_id not in tenant_policies:
            raise ValueError(
                "DOCPIPE_MCP_TENANT_ID must name a tenant in DOCPIPE_TENANT_PLUGIN_POLICIES."
            )
    elif settings.tenant_identity_map and settings.mcp_tenant_id not in set(
        settings.tenant_identity_map.values()
    ):
        raise ValueError(
            "DOCPIPE_MCP_TENANT_ID must be present in DOCPIPE_TENANT_IDENTITY_MAP values."
        )


app = create_app()
