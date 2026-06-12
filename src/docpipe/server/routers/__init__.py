"""Register domain routers on the FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from docpipe.server.routers import (
    agents,
    documents,
    evaluate,
    generate,
    ingest,
    meta,
    rag,
    transcribe,
)


def register_routers(app: FastAPI) -> None:
    for module in (
        meta,
        documents,
        ingest,
        rag,
        agents,
        evaluate,
        transcribe,
        generate,
    ):
        app.include_router(module.router)
