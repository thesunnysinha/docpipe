"""Jinja2 environment for server-rendered HTML pages."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@lru_cache(maxsize=1)
def get_jinja_env() -> Environment:
    """Return a cached Jinja environment rooted at ``server/templates``."""
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(name: str, **context: object) -> str:
    """Render a template from ``server/templates``."""
    return get_jinja_env().get_template(name).render(**context)
