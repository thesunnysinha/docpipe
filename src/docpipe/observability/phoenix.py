"""Optional Arize Phoenix tracing for evaluation runs."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_CONFIGURED = False


def configure_phoenix() -> None:
    """Register Phoenix OTLP when DOCPIPE_PHOENIX_ENABLED=true."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    from docpipe.config import get_settings

    settings = get_settings()
    if not settings.phoenix_enabled:
        _CONFIGURED = True
        return

    try:
        from phoenix.otel import register
    except ImportError:
        logger.warning(
            "DOCPIPE_PHOENIX_ENABLED but arize-phoenix is not installed. "
            "Install with: pip install docpipe-sdk[phoenix]"
        )
        _CONFIGURED = True
        return

    endpoint = settings.phoenix_collector_endpoint
    register(
        project_name=settings.otel_service_name,
        endpoint=endpoint,
        auto_instrument=True,
    )
    logger.info("Phoenix tracing enabled endpoint=%s", endpoint or "default")
    _CONFIGURED = True
