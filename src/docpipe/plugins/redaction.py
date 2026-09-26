"""Pure, bounded redaction for values crossing observability boundaries."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import TypeAlias
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

RedactedValue: TypeAlias = (
    None | bool | int | float | str | list["RedactedValue"] | dict[str, "RedactedValue"]
)

_SECRET_KEYS = {
    "api_key",
    "authorization",
    "client_secret",
    "credential",
    "credentials",
    "password",
    "passwd",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}
_SIGNED_QUERY_KEYS = {
    "sig",
    "signature",
    "x-amz-credential",
    "x-amz-security-token",
    "x-amz-signature",
    "x-goog-credential",
    "x-goog-signature",
}
_DSN_PASSWORD = re.compile(r"(?P<prefix>^[a-zA-Z][a-zA-Z0-9+.-]*://[^:/?#@]+:)[^@/?#]*(?=@)")
_INLINE_SECRET = re.compile(
    r"(?i)(?P<prefix>(?:api[_-]?key|authorization|password|secret|token)\s*[=:]\s*)"
    r"(?P<value>[^\s&,;]+)"
)


def redact(value: object, *, max_depth: int = 8) -> RedactedValue:
    """Return a JSON-compatible copy with secrets removed.

    Unsupported or malformed values are replaced rather than stringified because
    their representations can themselves contain credentials.
    """
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    return _redact(value, depth=0, max_depth=max_depth)


def _redact(value: object, *, depth: int, max_depth: int) -> RedactedValue:
    if depth >= max_depth:
        return REDACTED
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        try:
            return {
                str(key): (
                    REDACTED
                    if _is_secret_key(str(key))
                    else _redact(item, depth=depth + 1, max_depth=max_depth)
                )
                for key, item in value.items()
            }
        except Exception:
            return REDACTED
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        try:
            return [_redact(item, depth=depth + 1, max_depth=max_depth) for item in value]
        except Exception:
            return REDACTED
    return REDACTED


def _is_secret_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return normalized in _SECRET_KEYS or normalized.endswith("_secret")


def _redact_text(value: str) -> str:
    redacted = _DSN_PASSWORD.sub(r"\g<prefix>***", value)
    redacted = _INLINE_SECRET.sub(r"\g<prefix>***", redacted)
    return _redact_signed_query(redacted)


def _redact_signed_query(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if not parsed.query:
            return value
        query = [
            (key, "***" if key.lower() in _SIGNED_QUERY_KEYS else item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        ]
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
        )
    except ValueError:
        return REDACTED
