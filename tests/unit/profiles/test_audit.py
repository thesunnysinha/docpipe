"""Plugin resolution audit must not retain signed source URL credentials."""

from __future__ import annotations

import logging

import pytest

from docpipe.profiles.audit import log_plugin_resolve
from docpipe.profiles.resolve import _source_key, _source_scheme


def should_log_opaque_source_identity_instead_of_signed_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    signed_url = "https://example.test/document.pdf?X-Amz-Signature=secret-signature"
    caplog.set_level(logging.INFO, logger="docpipe.audit")

    log_plugin_resolve(
        source_scheme=_source_scheme(signed_url),
        source_key=_source_key(signed_url),
        goal="ingest",
        preset="balanced",
        recommended={"parser": "markitdown"},
    )

    assert signed_url not in caplog.text
    assert "secret-signature" not in caplog.text
    assert _source_key(signed_url) in caplog.text
