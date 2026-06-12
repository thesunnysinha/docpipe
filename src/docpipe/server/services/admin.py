"""Admin panel rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from docpipe.config import get_settings
from docpipe.db.repository import list_audit_events, list_ingest_jobs
from docpipe.server.template_env import render_template


@dataclass(frozen=True)
class AdminFlags:
    control_db_enabled: bool
    admin_panel_enabled: bool
    persist_audit_events: bool
    persist_ingest_jobs: bool
    persist_plugin_resolutions: bool
    control_db_url: str | None


class AdminService:
    def flags(self) -> AdminFlags:
        settings = get_settings()
        return AdminFlags(
            control_db_enabled=settings.control_db_enabled,
            admin_panel_enabled=settings.admin_panel_enabled,
            persist_audit_events=settings.persist_audit_events,
            persist_ingest_jobs=settings.persist_ingest_jobs,
            persist_plugin_resolutions=settings.persist_plugin_resolutions,
            control_db_url=settings.resolved_control_db_url(),
        )

    def dashboard_html(self) -> str:
        flags = self.flags()
        return render_template(
            "admin/dashboard.html",
            flags=flags,
        )

    def audit_html(self) -> str:
        flags = self.flags()
        events: list[Any] = list_audit_events(limit=100) if flags.persist_audit_events else []
        return render_template(
            "admin/audit.html",
            flags=flags,
            events=events,
        )

    def jobs_html(self) -> str:
        flags = self.flags()
        jobs: list[Any] = list_ingest_jobs(limit=100) if flags.persist_ingest_jobs else []
        return render_template(
            "admin/jobs.html",
            flags=flags,
            jobs=jobs,
        )
