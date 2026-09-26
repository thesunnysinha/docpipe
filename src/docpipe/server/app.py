"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from docpipe._version import __version__
from docpipe.bootstrap.server import create_server_lifespan, create_server_runtime
from docpipe.config.loader import load_config
from docpipe.config.settings import DocpipeSettings
from docpipe.server.bootstrap import (
    configure_app_runtime,
    register_exception_handlers,
)
from docpipe.server.routers import register_routers


def create_app(settings: DocpipeSettings | None = None) -> FastAPI:
    """Create and configure the docpipe FastAPI application."""
    resolved_settings = settings or load_config()
    runtime = create_server_runtime(resolved_settings)
    app = FastAPI(
        title="docpipe",
        description="Unified document parsing, extraction, and RAG ingestion API.",
        version=__version__,
        lifespan=create_server_lifespan(runtime),
    )
    app.state.docpipe_runtime = runtime
    configure_app_runtime(app, resolved_settings)
    register_exception_handlers(app)
    register_routers(app)
    return app


app = create_app()
