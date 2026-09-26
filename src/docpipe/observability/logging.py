"""Structured logging configuration with optional OTEL trace correlation."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize the record and available correlation fields as JSON.

        Output includes timestamp, level, logger, and rendered message, with
        trace/span IDs, request ID, and formatted exception details when
        available. Extra arbitrary log-record fields are not serialized.
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        trace_id, span_id = _otel_trace_ids()
        if trace_id:
            payload["trace_id"] = trace_id
        if span_id:
            payload["span_id"] = span_id
        request_id = getattr(record, "request_id", None)
        if request_id and request_id != "-":
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _otel_trace_ids() -> tuple[str | None, str | None]:
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if not ctx.is_valid:
            return None, None
        return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except ImportError:
        return None, None


def configure_logging(settings: Any) -> None:
    """Configure root log level and, if absent, a stdout structured handler.

    The configured level comes from ``settings.log_level``; ``settings`` may
    optionally provide ``log_format='json'``. The first call wins for the
    process because subsequent calls return immediately. If the root logger
    already has handlers, this function changes its level but does not replace
    or reformat those handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, str(settings.log_level).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        from docpipe.observability.request_context import RequestIdLogFilter

        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(RequestIdLogFilter())
        if getattr(settings, "log_format", "text") == "json":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] [req=%(request_id)s] %(name)s: %(message)s"
                )
            )
        root.addHandler(handler)
    _CONFIGURED = True
