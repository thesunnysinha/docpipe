"""OpenTelemetry TracerProvider setup (lazy, idempotent)."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CONFIGURED = False
_TRACER: Any = None


def configure_observability() -> None:
    """Configure OTLP export when DOCPIPE_OTEL_ENABLED=true. Idempotent."""
    global _CONFIGURED, _TRACER
    if _CONFIGURED:
        return

    from docpipe.config import get_settings

    settings = get_settings()
    if not settings.otel_enabled:
        _CONFIGURED = True
        return

    endpoint = settings.otel_exporter_otlp_endpoint
    if not endpoint:
        logger.warning("DOCPIPE_OTEL_ENABLED but DOCPIPE_OTEL_EXPORTER_OTLP_ENDPOINT is unset")
        _CONFIGURED = True
        return

    semconv = settings.otel_semconv_stability_opt_in
    if semconv:
        os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", semconv)

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import (
            ParentBasedTraceIdRatio,
            TraceIdRatioBased,
        )
    except ImportError:
        logger.warning(
            "OpenTelemetry packages not installed; pip install docpipe-sdk[observability]"
        )
        _CONFIGURED = True
        return

    sampler_name = settings.otel_traces_sampler.lower()
    ratio = max(0.0, min(1.0, settings.otel_traces_sampler_arg))
    if sampler_name in ("parentbased_traceidratio", "parentbased"):
        sampler = ParentBasedTraceIdRatio(ratio)
    else:
        sampler = TraceIdRatioBased(ratio)

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource, sampler=sampler)
    headers = _parse_otlp_headers(settings.otel_exporter_otlp_headers)
    exporter = OTLPSpanExporter(endpoint=str(endpoint), headers=headers or None)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _TRACER = trace.get_tracer(settings.otel_service_name)
    logger.info(
        "OpenTelemetry enabled endpoint=%s service=%s sample_ratio=%s",
        endpoint,
        settings.otel_service_name,
        ratio,
    )
    _CONFIGURED = True


def _parse_otlp_headers(raw: str | None) -> dict[str, str] | None:
    if not raw:
        return None
    headers: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            headers[key.strip()] = value.strip()
    return headers or None


def get_tracer() -> Any:
    """Return module tracer or None when OTEL is disabled/unavailable."""
    configure_observability()
    return _TRACER


def shutdown_observability() -> None:
    """Flush and shut down the TracerProvider."""
    global _CONFIGURED, _TRACER
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider

        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            provider.shutdown()
    except ImportError:
        pass
    except Exception:
        logger.exception("Failed to shut down OpenTelemetry")
    _TRACER = None
    _CONFIGURED = False


def instrument_fastapi(app: Any) -> None:
    """Instrument FastAPI when OTEL packages are installed."""
    configure_observability()
    if _TRACER is None:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        logger.warning("opentelemetry-instrumentation-fastapi not installed")
        return
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics",
        tracer_provider=None,
    )
