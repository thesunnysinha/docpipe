"""Persistence helpers for optional control-plane data."""

from __future__ import annotations

import json
from typing import Any

from docpipe.config import get_settings
from docpipe.db.models import AuditEvent, IngestJob
from docpipe.db.session import session_scope


def store_audit_event(*, event: str, tenant: str | None, payload: dict[str, Any]) -> None:
    """Persist an audit event when the corresponding settings enable it.

    Plugin-resolution records have an additional opt-in setting. Payload values
    are serialized to JSON with ``str`` as the fallback for non-JSON values.
    Disabled persistence is a no-op; database or serialization errors
    propagate. The operation commits through :func:`session_scope`.
    """
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
    """Persist ingest job metadata when job persistence is enabled.

    This stores the supplied source, table, preset/parser, counts, and status;
    it does not store document contents. Disabled persistence is a no-op.
    Database errors propagate from the managed transaction.
    """
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
    """Return up to ``limit`` audit events, newest identifier first.

    Results are materialized before the managed session closes. The query is
    not tenant-filtered; callers needing tenant isolation must enforce it
    before exposing these records. Database errors propagate.
    """
    from sqlalchemy import select

    with session_scope() as session:
        return list(session.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)))


def list_ingest_jobs(*, limit: int = 100) -> list[IngestJob]:
    """Return up to ``limit`` ingest jobs, newest identifier first.

    Results are materialized before the managed session closes. The query has
    no tenant filter, so callers must apply any required access control before
    exposing records. Database errors propagate.
    """
    from sqlalchemy import select

    with session_scope() as session:
        return list(session.scalars(select(IngestJob).order_by(IngestJob.id.desc()).limit(limit)))
