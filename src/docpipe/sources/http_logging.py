"""Request-scoped redaction of third-party HTTP source URL logs."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_SOURCE_REQUEST: ContextVar[bool] = ContextVar("docpipe_http_source_request", default=False)
_URL_PATTERN = re.compile(r"https?://[^\s\"']+")
_FILTER_INSTALLED = False


class SourceUrlLogFilter(logging.Filter):
    """Replace URL arguments while only a source download is active."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not _SOURCE_REQUEST.get():
            return True
        if isinstance(record.msg, str):
            record.msg = _URL_PATTERN.sub("<redacted-source-url>", record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(_mask_url(value) for value in record.args)
        elif isinstance(record.args, dict):
            record.args = {key: _mask_url(value) for key, value in record.args.items()}
        return True


def _mask_url(value: object) -> object:
    text = str(value)
    if "://" in text:
        return "<redacted-source-url>"
    return value


@contextmanager
def redact_source_http_logs() -> Iterator[None]:
    """Apply URL masking to HTTPX/HTTP Core logs for this task context only."""
    global _FILTER_INSTALLED
    if not _FILTER_INSTALLED:
        filter_ = SourceUrlLogFilter()
        for name in ("httpx", "httpcore.connection", "httpcore.http11", "httpcore.http2"):
            logging.getLogger(name).addFilter(filter_)
        _FILTER_INSTALLED = True
    token = _SOURCE_REQUEST.set(True)
    try:
        yield
    finally:
        _SOURCE_REQUEST.reset(token)
