"""FastAPI middleware helpers for observability enrichment."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from docpipe.observability.request_context import bind_request_id, reset_request_id

logger = logging.getLogger(__name__)

_SKIP_LOG_PREFIXES = ("/metrics",)


def _should_log_request(path: str, status_code: int) -> bool:
    """Decide whether to log a request, suppressing non-error metrics paths."""
    for prefix in _SKIP_LOG_PREFIXES:
        if path.startswith(prefix):
            return status_code >= 500
    return True


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP traffic with correlation IDs on ``X-Request-Id``."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Bind or generate a request ID around downstream HTTP handling.

        Adds the ID to request state and successful response headers, logs
        eligible responses with elapsed time, and enriches an active trace span.
        The context binding is always reset, including when downstream handling
        raises; raised exceptions are not caught or converted here.
        """
        request_id = (request.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
        request.state.request_id = request_id
        ctx_token = bind_request_id(request_id)
        try:
            start = time.perf_counter()
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000.0
            response.headers["X-Request-Id"] = request_id
            path = request.url.path
            if _should_log_request(path, response.status_code):
                logger.info(
                    "http_request method=%s path=%s status=%s duration_ms=%.1f",
                    request.method,
                    path,
                    response.status_code,
                    duration_ms,
                )
            enrich_http_span(request, response, request_id=request_id, duration_ms=duration_ms)
            return response
        finally:
            reset_request_id(ctx_token)


def enrich_http_span(
    request: Request,
    response: Response,
    *,
    request_id: str,
    duration_ms: float,
) -> None:
    """Attach request ID, duration, status, and route to a recording span.

    Does nothing when OpenTelemetry is unavailable or the current span is not
    recording. Span attributes contain routing metadata, not request/response
    bodies.
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if not span.is_recording():
            return
        span.set_attribute("http.request_id", request_id)
        span.set_attribute("http.duration_ms", duration_ms)
        span.set_attribute("http.status_code", response.status_code)
        route = request.scope.get("route")
        if route is not None:
            span.set_attribute("docpipe.route", getattr(route, "path", ""))
    except ImportError:
        return


def enrich_http_exception_span(request: Request, exc: Any) -> None:
    """Add error type, phase, and route attributes for structured details.

    Only dictionary-valued ``exc.detail`` is inspected. Does nothing without
    OpenTelemetry or a recording span; it does not record the exception itself.
    """
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
