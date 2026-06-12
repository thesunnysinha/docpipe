"""Homepage template rendering."""

from __future__ import annotations

from docpipe.server.homepage import render_homepage


def test_render_homepage_includes_version_and_plugins() -> None:
    html = render_homepage(
        version="0.6.0",
        profile="balanced",
        presets=[{"name": "fast", "description": "Low latency"}],
        parsers=["markitdown"],
        extractors=["langextract"],
    )
    assert "v0.6.0" in html
    assert "balanced" in html
    assert "markitdown" in html
    assert "langextract" in html
    assert "Runtime presets" in html
    assert "<!DOCTYPE html>" in html
