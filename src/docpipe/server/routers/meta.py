"""Homepage, health, plugins, and profiles."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from docpipe.profiles.guardrails import get_tenant_context
from docpipe.schemas import (
    HealthResponse,
    PluginResolveRequest,
    PluginResolveResponse,
    ProfilesResponse,
)
from docpipe.schemas.health import DependencyStatus
from docpipe.schemas.plugins import PluginsResponse
from docpipe.server.deps import Auth, DiscoveryServiceDep, RuntimeDep
from docpipe.server.licenses import render_pymupdf_license
from docpipe.server.plugin_health import probe_selected_vector

router = APIRouter(tags=["meta"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def homepage(_: Auth, service: DiscoveryServiceDep) -> HTMLResponse:
    return service.homepage()


@router.get("/health", response_model=HealthResponse)
async def health(service: DiscoveryServiceDep) -> HealthResponse:
    """Server health — no auth required (used by Docker healthcheck)."""
    return service.health()


@router.get("/plugins", response_model=PluginsResponse)
async def list_plugins(_: Auth, service: DiscoveryServiceDep) -> PluginsResponse:
    """List registered plugins grouped by capability."""
    return service.list_plugins(tenant_id=get_tenant_context())


@router.get("/plugins/health", response_model=DependencyStatus)
async def selected_plugin_health(_: Auth, runtime: RuntimeDep) -> DependencyStatus:
    """Explicitly probe only the configured vector plugin with a deadline."""
    return await probe_selected_vector(runtime)


@router.get("/profiles", response_model=ProfilesResponse)
async def list_profiles(_: Auth, service: DiscoveryServiceDep) -> ProfilesResponse:
    return service.list_profiles()


@router.get("/licenses/pymupdf", response_class=HTMLResponse, include_in_schema=False)
async def pymupdf_license(_: Auth) -> HTMLResponse:
    """Commercial license notes for the optional pymupdf parser."""
    return HTMLResponse(content=render_pymupdf_license())


@router.post("/plugins/resolve", response_model=PluginResolveResponse)
async def plugins_resolve(
    req: PluginResolveRequest,
    _: Auth,
    service: DiscoveryServiceDep,
) -> PluginResolveResponse:
    try:
        return service.resolve_plugins(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
