"""Register domain routers on the FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from docpipe.server.routers import (
    admin,
    agents,
    cost,
    documents,
    evaluate,
    generate,
    ingest,
    mcp,
    meta,
    rag,
    transcribe,
)


def register_routers(app: FastAPI) -> None:
    """Mount the server's HTTP router modules on ``app`` in stable order."""
    for module in (
        meta,
        admin,
        documents,
        ingest,
        rag,
        agents,
        cost,
        mcp,
        evaluate,
        transcribe,
        generate,
    ):
        app.include_router(module.router)
