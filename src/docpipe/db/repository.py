"""Persistence helpers for optional control-plane data."""

from __future__ import annotations

import json
from typing import Any

from docpipe.config import get_settings
from docpipe.db.models import AuditEvent, IngestJob
from docpipe.db.session import session_scope


def store_audit_event(*, event: str, tenant: str | None, payload: dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.control_db_enabled or not settings.persist_audit_events:
        return
    if event == "plugin_resolve" and not settings.persist_plugin_resolutions:
        return

    with session_scope() as session:
        session.add(
            AuditEvent(
                event=event,
                tenant=tenant,
                payload_json=json.dumps(payload, default=str),
            )
        )


def store_ingest_job(
    *,
    source: str,
    table_name: str,
    preset: str | None,
    parser: str | None,
    chunks_ingested: int,
    skipped: int,
    status: str = "completed",
) -> None:
    settings = get_settings()
    if not settings.control_db_enabled or not settings.persist_ingest_jobs:
        return

    with session_scope() as session:
        session.add(
            IngestJob(
                source=source,
                table_name=table_name,
                preset=preset,
                parser=parser,
                chunks_ingested=chunks_ingested,
                skipped=skipped,
                status=status,
            )
        )


def list_audit_events(*, limit: int = 100) -> list[AuditEvent]:
    from sqlalchemy import select

    with session_scope() as session:
        return list(session.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)))


def list_ingest_jobs(*, limit: int = 100) -> list[IngestJob]:
    from sqlalchemy import select

    with session_scope() as session:
        return list(session.scalars(select(IngestJob).order_by(IngestJob.id.desc()).limit(limit)))
