"""Application factory wiring: lifespan, middleware, exception handlers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from docpipe.config.settings import DocpipeSettings
from docpipe.observability import (
    configure_logging,
    configure_observability,
    shutdown_observability,
)
from docpipe.observability.metrics import setup_prometheus_instrumentation
from docpipe.observability.middleware import (
    RequestResponseLoggingMiddleware,
    enrich_http_exception_span,
)
from docpipe.observability.tracing import instrument_fastapi
from docpipe.server.http_errors import record_http_error_metrics


def configure_app_runtime(app: FastAPI, settings: DocpipeSettings) -> None:
    """Attach observability middleware and instrumentation."""
    configure_logging(settings)
    configure_observability()
    setup_prometheus_instrumentation(app)
    instrument_fastapi(app)
    if settings.http_request_logging_enabled:
        app.add_middleware(RequestResponseLoggingMiddleware)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    yield
    shutdown_observability()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Any:
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
