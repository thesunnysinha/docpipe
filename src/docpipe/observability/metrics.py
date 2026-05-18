"""Prometheus metrics for docpipe HTTP and pipeline operations."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

try:
    from prometheus_client import Counter, Histogram
except ImportError:  # pragma: no cover - optional dependency
    Counter = None  # type: ignore[misc, assignment]
    Histogram = None  # type: ignore[misc, assignment]

INGEST_CHUNKS: Counter | None
RAG_QUERY_DURATION: Histogram | None
ERRORS_TOTAL: Counter | None

if Counter is not None and Histogram is not None:
    INGEST_CHUNKS = Counter(
        "docpipe_ingest_chunks_total",
        "Total document chunks ingested",
        ["table_name"],
    )
    RAG_QUERY_DURATION = Histogram(
        "docpipe_rag_query_duration_seconds",
        "RAG query duration in seconds",
        ["strategy", "status"],
    )
    ERRORS_TOTAL = Counter(
        "docpipe_errors_total",
        "HTTP errors by type and phase",
        ["error_type", "phase", "handler"],
    )
else:
    INGEST_CHUNKS = None
    RAG_QUERY_DURATION = None
    ERRORS_TOTAL = None


def metrics_available() -> bool:
    return INGEST_CHUNKS is not None


def record_ingest(table_name: str, chunks: int) -> None:
    if INGEST_CHUNKS is not None and chunks > 0:
        INGEST_CHUNKS.labels(table_name=table_name).inc(chunks)


def record_rag(duration_seconds: float, strategy: str, *, ok: bool) -> None:
    if RAG_QUERY_DURATION is not None:
        status = "ok" if ok else "error"
        RAG_QUERY_DURATION.labels(strategy=strategy, status=status).observe(duration_seconds)


def record_error(error_type: str, phase: str, handler: str) -> None:
    if ERRORS_TOTAL is not None:
        ERRORS_TOTAL.labels(
            error_type=error_type,
            phase=phase,
            handler=handler,
        ).inc()


@contextmanager
def observe_rag(strategy: str) -> Generator[None, None, None]:
    """Observe RAG query duration on success or failure."""
    start = time.perf_counter()
    ok = True
    try:
        yield
    except Exception:
        ok = False
        raise
    finally:
        record_rag(time.perf_counter() - start, strategy, ok=ok)


def setup_prometheus_instrumentation(app: object) -> None:
    """Expose /metrics via prometheus-fastapi-instrumentator when installed."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError:
        return
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
