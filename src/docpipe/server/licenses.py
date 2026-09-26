"""HTML license guidance pages."""

from __future__ import annotations

from docpipe.server.template_env import get_jinja_env


def render_pymupdf_license() -> str:
    """Render the bundled PyMuPDF license notice as an HTML document."""
    template = get_jinja_env().get_template("licenses/pymupdf.html")
    return template.render()
