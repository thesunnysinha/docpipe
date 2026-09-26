"""Wire server-wide middleware, telemetry, and HTTP exception handling.

Application lifespan and runtime construction live in ``bootstrap.server``;
this module configures cross-cutting FastAPI behavior after the app exists.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from docpipe.config.settings import DocpipeSettings
from docpipe.observability import (
    configure_logging,
    configure_observability,
)
from docpipe.observability.metrics import setup_prometheus_instrumentation
from docpipe.observability.middleware import (
    RequestResponseLoggingMiddleware,
    enrich_http_exception_span,
)
from docpipe.observability.phoenix import configure_phoenix
from docpipe.observability.tracing import instrument_fastapi
from docpipe.server.http_errors import record_http_error_metrics
from docpipe.server.rate_limit import PresetRateLimitMiddleware
from docpipe.server.tenant_middleware import TenantContextMiddleware


def configure_app_runtime(app: FastAPI, settings: DocpipeSettings) -> None:
    """Configure logging, telemetry, tracing, and request middleware.

    Tenant context and body-free rate limiting are installed before route
    processing. Request/response logging is conditional on settings; core
    metrics and tracing instrumentation are configured for the application.
    """
    configure_logging(settings)
    configure_observability()
    configure_phoenix()
    setup_prometheus_instrumentation(app)
    app.add_middleware(TenantContextMiddleware)
    # The body-free limiter must run before tenant credential checks and route
    # authentication so unauthenticated traffic is bounded first.
    app.add_middleware(PresetRateLimitMiddleware)
    instrument_fastapi(app)
    if settings.http_request_logging_enabled:
        app.add_middleware(RequestResponseLoggingMiddleware)


def register_exception_handlers(app: FastAPI) -> None:
    """Register the shared HTTP exception response and telemetry handler.

    The handler preserves the exception status and detail shape, enriches the
    active trace, and records error metrics only for structured error details.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Any:
        """Preserve the HTTP error payload and record structured telemetry."""
        enrich_http_exception_span(request, exc)
        detail = exc.detail
        if isinstance(detail, dict):
            route = request.scope.get("route")
            handler = getattr(route, "path", "unknown") if route else "unknown"
            record_http_error_metrics(
                str(detail.get("error_type", "docpipe")),
                str(detail.get("phase", "unknown")),
                handler,
            )
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})
