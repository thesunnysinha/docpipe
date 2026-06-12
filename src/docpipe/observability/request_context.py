"""Request-scoped correlation IDs for logging and tracing."""

from __future__ import annotations

import contextvars
import logging

CORRELATION_ID_HEADER = "X-Request-Id"

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


def bind_request_id(request_id: str | None) -> contextvars.Token[str | None]:
    return _request_id.set(request_id)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    _request_id.reset(token)


def outbound_correlation_headers() -> dict[str, str]:
    """Headers for outbound httpx calls during an active docpipe request."""
    rid = get_request_id()
    if not rid:
        return {}
    return {CORRELATION_ID_HEADER: rid}


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"  # type: ignore[attr-defined]
        return True
