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
PRESET_USAGE: Counter | None
PLUGIN_DENIED: Counter | None

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
    PRESET_USAGE = Counter(
        "docpipe_preset_usage_total",
        "API requests using a runtime preset",
        ["preset", "endpoint"],
    )
    PLUGIN_DENIED = Counter(
        "docpipe_plugin_denied_total",
        "Plugin guardrail denials",
        ["group", "name"],
    )
else:
    INGEST_CHUNKS = None
    RAG_QUERY_DURATION = None
    ERRORS_TOTAL = None
    PRESET_USAGE = None
    PLUGIN_DENIED = None


def metrics_available() -> bool:
    """Return whether the optional Prometheus client registered metrics."""
    return INGEST_CHUNKS is not None


def record_ingest(table_name: str, chunks: int) -> None:
    """Add a positive ingested-chunk count for the supplied table label.

    This is a no-op when Prometheus is unavailable or ``chunks`` is not
    positive. The label is emitted as provided, so callers should pass stable,
    bounded table identifiers rather than per-document values.
    """
    if INGEST_CHUNKS is not None and chunks > 0:
        INGEST_CHUNKS.labels(table_name=table_name).inc(chunks)


def record_rag(duration_seconds: float, strategy: str, *, ok: bool) -> None:
    """Observe RAG duration with strategy and ``ok``/``error`` status labels.

    This is a no-op when the optional Prometheus client is unavailable.
    """
    if RAG_QUERY_DURATION is not None:
        status = "ok" if ok else "error"
        RAG_QUERY_DURATION.labels(strategy=strategy, status=status).observe(duration_seconds)


def record_error(error_type: str, phase: str, handler: str) -> None:
    """Increment the error counter for the supplied categorical labels."""
    if ERRORS_TOTAL is not None:
        ERRORS_TOTAL.labels(
            error_type=error_type,
            phase=phase,
            handler=handler,
        ).inc()


def record_preset_usage(preset: str, endpoint: str) -> None:
    """Increment preset usage when metrics are available and preset is nonempty."""
    if PRESET_USAGE is not None and preset:
        PRESET_USAGE.labels(preset=preset, endpoint=endpoint).inc()


def record_plugin_denied(group: str, name: str) -> None:
    """Increment the plugin-denial counter for the supplied plugin labels."""
    if PLUGIN_DENIED is not None:
        PLUGIN_DENIED.labels(group=group, name=name).inc()


@contextmanager
def observe_rag(strategy: str) -> Generator[None, None, None]:
    """Observe elapsed RAG operation time, including failed operations.

    Records an ``ok`` status if the context exits normally and ``error`` if an
    exception escapes. Exceptions are re-raised unchanged after observation.
    Metrics collection is optional and can be a no-op.
    """
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
    """Install FastAPI HTTP instrumentation and expose ``/metrics`` if present.

    The optional instrumentator dependency is imported lazily; if it is not
    installed, this function returns without modifying the app. Health and
    metrics handlers are excluded from request instrumentation, and
    untemplated routes are ignored.
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError:
        return
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
