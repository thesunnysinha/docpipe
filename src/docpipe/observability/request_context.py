"""Request-scoped correlation IDs for logging and tracing."""

from __future__ import annotations

import contextvars
import logging

CORRELATION_ID_HEADER = "X-Request-Id"

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Return the correlation ID bound to the current execution context."""
    return _request_id.get()


def bind_request_id(request_id: str | None) -> contextvars.Token[str | None]:
    """Bind a request ID and return the token required to restore prior state.

    Context-variable scope follows the current async/task context. Callers
    should retain the returned token and pass it to :func:`reset_request_id`
    in a ``finally`` block to avoid leaking context into later work.
    """
    return _request_id.set(request_id)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    """Restore the request-ID context to the value preceding its binding."""
    _request_id.reset(token)


def outbound_correlation_headers() -> dict[str, str]:
    """Headers for outbound httpx calls during an active docpipe request."""
    rid = get_request_id()
    if not rid:
        return {}
    return {CORRELATION_ID_HEADER: rid}


class RequestIdLogFilter(logging.Filter):
    """Attach the current request ID, or ``-``, to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Set ``record.request_id`` and allow the record to be logged."""
        record.request_id = get_request_id() or "-"  # type: ignore[attr-defined]
        return True
