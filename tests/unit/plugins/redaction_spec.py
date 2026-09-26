"""Tests for recursive credential and URL redaction."""

from __future__ import annotations

from docpipe.plugins.redaction import REDACTED, redact


def test_redact_masks_nested_secret_fields() -> None:
    value = {
        "provider": "qdrant",
        "options": {
            "api_key": "secret",
            "nested": [{"Authorization": "Bearer token"}],
        },
    }

    assert redact(value) == {
        "provider": "qdrant",
        "options": {"api_key": REDACTED, "nested": [{"Authorization": REDACTED}]},
    }


def test_redact_masks_dsn_credentials_and_signed_url_query() -> None:
    value = {
        "connection": "postgresql://admin:secret@db/documents",
        "url": "https://store.example/doc.pdf?X-Amz-Signature=abc&part=1",
    }

    redacted = redact(value)

    assert redacted["connection"] == "postgresql://admin:***@db/documents"
    assert redacted["url"] == "https://store.example/doc.pdf?X-Amz-Signature=%2A%2A%2A&part=1"


def test_redact_bounds_recursive_input() -> None:
    value: object = "leaf"
    for _ in range(20):
        value = {"safe": value}

    result = redact(value, max_depth=3)

    assert result == {"safe": {"safe": {"safe": REDACTED}}}
