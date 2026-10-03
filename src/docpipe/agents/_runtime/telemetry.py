"""Structured logging (structlog) and optional tracing (OpenTelemetry, Langfuse).

Call ``configure_telemetry(settings)`` once at startup. Without it, settings come from the
environment (``LOG_FORMAT``, ``ENVIRONMENT``, ``OTEL_*``, ``LANGFUSE_*``). Tracing packages are
imported only when the matching keys are set, so a plain project needs neither.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import structlog


@dataclass
class TelemetrySettings:
    environment: str = field(default_factory=lambda: os.environ.get("ENVIRONMENT", "development"))
    log_format: str = field(default_factory=lambda: os.environ.get("LOG_FORMAT", "auto"))  # auto | console | json
    debug: bool = field(default_factory=lambda: os.environ.get("DEBUG", "").lower() in {"1", "true"})
    service_name: str = field(default_factory=lambda: os.environ.get("OTEL_SERVICE_NAME", "agent-service"))
    trace_name: str = "agent"
    otel_endpoint: Optional[str] = field(default_factory=lambda: os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))
    otel_headers: Optional[str] = field(default_factory=lambda: os.environ.get("OTEL_EXPORTER_OTLP_HEADERS"))
    langfuse_public_key: Optional[str] = field(default_factory=lambda: os.environ.get("LANGFUSE_PUBLIC_KEY"))
    langfuse_secret_key: Optional[str] = field(default_factory=lambda: os.environ.get("LANGFUSE_SECRET_KEY"))
    langfuse_base_url: str = field(default_factory=lambda: os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"))


_settings = TelemetrySettings()


def add_otel_context(_: Any, __: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from opentelemetry import trace
    except ImportError:
        return event_dict
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["otel_trace_id"] = format(span_context.trace_id, "032x")
        event_dict["otel_span_id"] = format(span_context.span_id, "016x")
    return event_dict


def parse_otlp_headers(raw: Optional[str]) -> Dict[str, str]:
    """Parse the standard OTEL_EXPORTER_OTLP_HEADERS format: comma separated, URL-encoded key=value pairs."""
    headers: Dict[str, str] = {}
    for pair in (raw or "").split(","):
        key, sep, value = pair.partition("=")
        if sep and key.strip():
            headers[key.strip()] = unquote(value.strip())
    return headers


def _use_json() -> bool:
    if _settings.log_format == "auto":
        return _settings.environment != "development"
    return _settings.log_format == "json"


def configure_logging() -> None:
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_otel_context,
        structlog.processors.StackInfoRenderer(),
    ]
    if _use_json():
        renderer: Any = structlog.processors.JSONRenderer()
        exception_processors: list = [structlog.processors.dict_tracebacks]
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty() and "NO_COLOR" not in os.environ)
        exception_processors = []

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *exception_processors, renderer],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.DEBUG if _settings.debug else logging.INFO)
    for noisy in ("httpx", "httpcore", "openai", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def configure_telemetry(settings: Optional[TelemetrySettings] = None) -> None:
    """Install the logging pipeline for this process (idempotent)."""
    global _settings
    _settings = settings or TelemetrySettings()
    configure_logging()


def get_logger(name: str = "agent") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


logger = get_logger("telemetry")


def langfuse_enabled() -> bool:
    return bool(_settings.langfuse_public_key and _settings.langfuse_secret_key)


def tracing_callbacks() -> List[Any]:
    """LangChain callbacks for the agent graph: the Langfuse handler when configured, otherwise none."""
    if not langfuse_enabled():
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler(public_key=_settings.langfuse_public_key)]


def trace_context(session_id: str, trace_id: str) -> AbstractContextManager:
    """Tag everything traced inside the block with the session and request trace id (no-op without Langfuse)."""
    if not langfuse_enabled():
        return nullcontext()
    from langfuse import propagate_attributes

    return propagate_attributes(session_id=session_id, trace_name=_settings.trace_name, metadata={"trace_id": trace_id})


def shutdown_tracing() -> None:
    if langfuse_enabled():
        from langfuse import get_client

        get_client().flush()


def setup_tracing() -> None:
    """Start Langfuse, or OpenTelemetry export when only an OTLP endpoint is set. Never raises."""
    if langfuse_enabled():
        # Langfuse's LangChain handler already records every model/tool/graph step, so the OpenInference
        # instrumentation is skipped in this mode to avoid duplicate spans.
        try:
            from langfuse import Langfuse

            Langfuse(
                public_key=_settings.langfuse_public_key,
                secret_key=_settings.langfuse_secret_key,
                base_url=_settings.langfuse_base_url,
                environment=_settings.environment,
            )
            logger.info("telemetry.langfuse.enabled", base_url=_settings.langfuse_base_url)
        except Exception as exc:
            logger.warning("telemetry.langfuse.bootstrap_failed", error=str(exc))
        return

    if not _settings.otel_endpoint:
        logger.info("telemetry.otel.disabled", reason="OTEL_EXPORTER_OTLP_ENDPOINT not set")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from openinference.instrumentation.langchain import LangChainInstrumentor

        provider = TracerProvider(resource=Resource.create({"service.name": _settings.service_name}))
        exporter = OTLPSpanExporter(
            endpoint=f"{_settings.otel_endpoint.rstrip('/')}/v1/traces",
            headers=parse_otlp_headers(_settings.otel_headers) or None,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        LangChainInstrumentor().instrument()
        logger.info("telemetry.otel.enabled", endpoint=_settings.otel_endpoint)
    except Exception as exc:
        logger.warning("telemetry.otel.bootstrap_failed", error=str(exc))
