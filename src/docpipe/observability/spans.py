"""Manual span helpers with GenAI semantic convention attributes."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from docpipe.observability.tracing import get_tracer


def _provider_semconv_name(provider: str | None) -> str | None:
    if not provider:
        return None
    mapping = {
        "openai": "openai",
        "google": "google",
        "anthropic": "anthropic",
        "ollama": "ollama",
        "azure": "azure.ai.openai",
    }
    return mapping.get(provider.lower(), provider.lower())


@contextmanager
def trace_operation(
    name: str,
    *,
    gen_ai_operation: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    **attrs: Any,
) -> Generator[Any, None, None]:
    """Start a span when tracing is enabled; no-op otherwise."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    attributes: dict[str, Any] = dict(attrs)
    if gen_ai_operation:
        attributes["gen_ai.operation.name"] = gen_ai_operation
    semconv_provider = _provider_semconv_name(provider)
    if semconv_provider:
        attributes["gen_ai.provider.name"] = semconv_provider
    if model:
        attributes["gen_ai.request.model"] = model

    with tracer.start_as_current_span(name, attributes=attributes) as span:
        yield span


def set_gen_ai_usage(span: Any, usage: dict[str, int | None] | None) -> None:
    """Attach token usage attributes to the active span."""
    if span is None or not usage:
        return
    if usage.get("input_tokens") is not None:
        span.set_attribute("gen_ai.usage.input_tokens", int(usage["input_tokens"]))
    if usage.get("output_tokens") is not None:
        span.set_attribute("gen_ai.usage.output_tokens", int(usage["output_tokens"]))
    total = usage.get("total_tokens")
    if total is not None:
        span.set_attribute("gen_ai.usage.total_tokens", int(total))
