"""FastAPI middleware helpers for observability enrichment."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request


def enrich_http_exception_span(request: Request, exc: Any) -> None:
    """Add docpipe error attributes to the current span when present."""
    detail = getattr(exc, "detail", None)
    if not isinstance(detail, dict):
        return
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if not span.is_recording():
            return
        error_type = detail.get("error_type")
        phase = detail.get("phase")
        if error_type:
            span.set_attribute("docpipe.error_type", error_type)
        if phase:
            span.set_attribute("docpipe.phase", phase)
        route = request.scope.get("route")
        if route is not None:
            span.set_attribute("docpipe.route", getattr(route, "path", ""))
    except ImportError:
        return
