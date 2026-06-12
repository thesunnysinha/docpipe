"""SSRF guard tests."""

from __future__ import annotations

import pytest

from docpipe.core.errors import ParseError
from docpipe.parsers.url_safety import assert_safe_http_source


def test_local_file_skips_url_guard() -> None:
    assert_safe_http_source("/tmp/report.pdf")


def test_private_url_blocked_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from docpipe.config.settings import DocpipeSettings

    monkeypatch.setattr(
        "docpipe.parsers.url_safety.get_settings",
        lambda: DocpipeSettings(allow_private_urls=False),
    )

    with pytest.raises(ParseError, match="private network"):
        assert_safe_http_source("http://127.0.0.1/secret.pdf")
