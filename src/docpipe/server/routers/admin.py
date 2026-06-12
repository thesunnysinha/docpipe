"""Optional admin panel for control-plane database."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from docpipe.config import get_settings
from docpipe.server.deps import AdminServiceDep, Auth

router = APIRouter(tags=["admin"])


def _ensure_admin_panel() -> None:
    settings = get_settings()
    if not settings.control_db_enabled or not settings.admin_panel_enabled:
        raise HTTPException(status_code=404, detail="Admin panel is disabled")


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard(_: Auth, service: AdminServiceDep) -> HTMLResponse:
    _ensure_admin_panel()
    return HTMLResponse(content=service.dashboard_html())


@router.get("/admin/audit", response_class=HTMLResponse, include_in_schema=False)
async def admin_audit(_: Auth, service: AdminServiceDep) -> HTMLResponse:
    _ensure_admin_panel()
    return HTMLResponse(content=service.audit_html())


@router.get("/admin/jobs", response_class=HTMLResponse, include_in_schema=False)
async def admin_jobs(_: Auth, service: AdminServiceDep) -> HTMLResponse:
    _ensure_admin_panel()
    return HTMLResponse(content=service.jobs_html())
