"""Map DocpipeError instances to HTTP responses with actionable detail."""

from __future__ import annotations

from fastapi import HTTPException

from docpipe.core.errors import (
    ConfigurationError,
    DocpipeError,
    IngestionError,
    ParseError,
    RAGError,
)

# Google retired models/embedding-001 on v1beta; callers still copy old examples.
DEPRECATED_GOOGLE_EMBEDDING_MODELS = frozenset({"models/embedding-001", "embedding-001"})


def _infer_phase(exc: DocpipeError, message: str) -> str:
    lower = message.lower()
    if isinstance(exc, ParseError):
        return "parse"
    if isinstance(exc, IngestionError):
        if "vector store" in lower or "embed" in lower:
            return "embedding"
        return "ingestion"
    if isinstance(exc, RAGError):
        if "embed" in lower or "retriev" in lower:
            return "embedding"
        if "generat" in lower or "llm" in lower:
            return "generation"
        return "rag"
    return "unknown"


def _is_upstream_provider_failure(message: str) -> bool:
    lower = message.lower()
    markers = (
        "not_found",
        "resource_exhausted",
        "quota exceeded",
        "invalid api key",
        "api key not valid",
        "permission denied",
        "unauthenticated",
        "rate limit",
        " 401 ",
        " 403 ",
        " 429 ",
        "error embedding content",
    )
    return any(marker in lower for marker in markers)


def docpipe_http_exception(exc: DocpipeError) -> HTTPException:
    """Raise an HTTPException with structured detail for API clients."""
    message = str(exc)
    phase = _infer_phase(exc, message)
    error_type = "docpipe"

    if isinstance(exc, ConfigurationError):
        error_type = "configuration"
        status = 400
    elif _is_upstream_provider_failure(message):
        error_type = "upstream_provider"
        status = 502
    else:
        status = 400

    detail: dict[str, str] = {
        "message": message,
        "error_type": error_type,
        "phase": phase,
    }

    if phase == "embedding" and "embedding_model" not in message:
        # Hint when Google model id is stale (common default in older configs).
        for deprecated in DEPRECATED_GOOGLE_EMBEDDING_MODELS:
            if deprecated in message:
                detail["hint"] = (
                    f"Model '{deprecated}' is no longer served by the Gemini API. "
                    "Use models/text-embedding-004 or models/gemini-embedding-001."
                )
                break

    return HTTPException(status_code=status, detail=detail)


def record_http_error_metrics(error_type: str, phase: str, handler: str = "unknown") -> None:
    """Increment Prometheus error counter when metrics are available."""
    try:
        from docpipe.observability.metrics import record_error

        record_error(error_type, phase, handler)
    except ImportError:
        return
