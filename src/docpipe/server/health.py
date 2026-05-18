"""Dependency probes for the /health endpoint."""

from __future__ import annotations

import time
from typing import Literal

import psycopg2
from pydantic import BaseModel, Field

from docpipe.config import get_settings


class DependencyStatus(BaseModel):
    name: str
    status: Literal["ok", "degraded", "unavailable"]
    latency_ms: float | None = None
    detail: str | None = None


class ExtendedHealthResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    version: str
    plugins: dict[str, list[str]]
    dependencies: list[DependencyStatus] = Field(default_factory=list)


def check_database(connection_string: str | None) -> DependencyStatus:
    """Run SELECT 1 against the configured database."""
    if not connection_string:
        return DependencyStatus(
            name="database",
            status="unavailable",
            detail="DOCPIPE_DB_CONNECTION_STRING is not set",
        )
    start = time.perf_counter()
    try:
        with psycopg2.connect(connection_string, connect_timeout=3) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        latency_ms = (time.perf_counter() - start) * 1000
        return DependencyStatus(name="database", status="ok", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - start) * 1000
        return DependencyStatus(
            name="database",
            status="unavailable",
            latency_ms=latency_ms,
            detail=str(exc),
        )


def check_embedding_provider() -> DependencyStatus:
    """Optional lightweight embedding probe (disabled by default)."""
    settings = get_settings()
    provider = settings.embedding_provider
    model = settings.embedding_model
    if not provider or not model:
        return DependencyStatus(
            name="embedding_provider",
            status="degraded",
            detail="embedding provider/model not configured",
        )
    start = time.perf_counter()
    try:
        from docpipe.core.types import RAGConfig
        from docpipe.rag.pipeline import RAGPipeline

        config = RAGConfig(
            connection_string=settings.db_connection_string or "postgresql://localhost/docpipe",
            table_name="health_probe",
            embedding_provider=provider,
            embedding_model=model,
            llm_provider="openai",
            llm_model="gpt-4o-mini",
        )
        embeddings = RAGPipeline._create_embeddings(config)
        embeddings.embed_query("health")
        latency_ms = (time.perf_counter() - start) * 1000
        return DependencyStatus(name="embedding_provider", status="ok", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - start) * 1000
        return DependencyStatus(
            name="embedding_provider",
            status="degraded",
            latency_ms=latency_ms,
            detail=str(exc),
        )


def build_health_response(version: str, plugins: dict[str, list[str]]) -> ExtendedHealthResponse:
    """Aggregate dependency checks into an overall health status."""
    settings = get_settings()
    dependencies: list[DependencyStatus] = []

    if settings.health_check_db:
        if settings.db_connection_string:
            db_status = check_database(settings.db_connection_string)
            dependencies.append(db_status)
        else:
            db_status = DependencyStatus(
                name="database",
                status="ok",
                detail="skipped (DOCPIPE_DB_CONNECTION_STRING unset)",
            )
            dependencies.append(db_status)
    else:
        db_status = None

    if settings.health_check_embedding:
        emb_status = check_embedding_provider()
        dependencies.append(emb_status)
    else:
        emb_status = None

    overall: Literal["ok", "degraded", "unavailable"] = "ok"
    if db_status is not None and db_status.status == "unavailable":
        overall = "unavailable"
    elif emb_status is not None and emb_status.status == "degraded" and overall == "ok":
        overall = "degraded"

    return ExtendedHealthResponse(
        status=overall,
        version=version,
        plugins=plugins,
        dependencies=dependencies,
    )
