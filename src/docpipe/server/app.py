"""FastAPI application factory."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from docpipe._version import __version__
from docpipe.config import get_settings
from docpipe.server.bootstrap import (
    app_lifespan,
    configure_app_runtime,
    register_exception_handlers,
)
from docpipe.server.routers import register_routers


def create_app() -> Any:
    """Create and configure the docpipe FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title="docpipe",
        description="Unified document parsing, extraction, and RAG ingestion API.",
        version=__version__,
        lifespan=app_lifespan,
    )
    configure_app_runtime(app, settings)
    register_exception_handlers(app)
    register_routers(app)
    return app


app = create_app()
