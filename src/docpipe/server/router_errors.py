"""Translate service-layer errors into HTTP responses."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from docpipe.core.errors import DocpipeError
from docpipe.server.http_errors import docpipe_http_exception

P = ParamSpec("P")
T = TypeVar("T")


def handle_docpipe_errors(
    func: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    """Decorator for thin routers: map DocpipeError to structured HTTP errors."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except DocpipeError as exc:
            raise docpipe_http_exception(exc) from exc

    return wrapper
