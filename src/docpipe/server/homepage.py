"""Homepage HTML for the docpipe web UI."""

from __future__ import annotations

from docpipe.server.template_env import get_jinja_env


def render_homepage(
    version: str,
    profile: str,
    presets: list[dict[str, str]],
    parsers: list[str],
    extractors: list[str],
) -> str:
    """Render the server landing page from Jinja templates."""
    template = get_jinja_env().get_template("homepage.html")
    return template.render(
        version=version,
        profile=profile,
        presets=presets,
        parsers=parsers,
        extractors=extractors,
    )
