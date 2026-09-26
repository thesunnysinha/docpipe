"""Translate service-layer errors into HTTP responses."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from docpipe.core.errors import DocpipeError
from docpipe.plugins.errors import PublicIntegrationError
from docpipe.server.http_errors import docpipe_http_exception, integration_http_exception

P = ParamSpec("P")
T = TypeVar("T")


def handle_docpipe_errors(
    func: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    """Wrap an async route/service call with public HTTP error translation.

    Domain ``DocpipeError`` and sanitized ``PublicIntegrationError`` instances
    are mapped to structured HTTP exceptions. Other exceptions propagate to
    FastAPI's normal error handling. ``wraps`` preserves the wrapped callable's
    metadata and the ParamSpec keeps its call signature for type checkers.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        """Translate known domain errors while preserving other failures."""
        try:
            return await func(*args, **kwargs)
        except DocpipeError as exc:
            raise docpipe_http_exception(exc) from exc
        except PublicIntegrationError as exc:
            raise integration_http_exception(exc) from exc

    return wrapper
