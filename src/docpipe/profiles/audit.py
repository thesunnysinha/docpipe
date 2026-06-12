"""Structured audit events for plugin policy and resolution."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("docpipe.audit")


def _emit(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, default=str))
    try:
        from docpipe.db.repository import store_audit_event

        store_audit_event(
            event=event,
            tenant=fields.get("tenant"),
            payload=payload,
        )
    except Exception:  # noqa: BLE001
        logger.debug("audit persistence skipped", exc_info=True)


def log_plugin_denied(*, group: str, name: str, tenant: str | None = None) -> None:
    _emit("plugin_denied", group=group, plugin=name, tenant=tenant)


def log_plugin_resolve(
    *,
    source: str | None,
    goal: str,
    preset: str | None,
    recommended: dict[str, Any],
    tenant: str | None = None,
) -> None:
    _emit(
        "plugin_resolve",
        source=source,
        goal=goal,
        preset=preset,
        recommended=recommended,
        tenant=tenant,
    )
