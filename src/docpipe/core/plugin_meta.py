"""Shared metadata helpers for docpipe plugins."""

from __future__ import annotations

from typing import Any


def plugin_info_dict(cls: type[Any], *, name: str | None = None) -> dict[str, Any]:
    """Build a standard plugin info dict from a plugin class."""
    return {
        "name": name or getattr(cls, "name", cls.__qualname__),
        "class": f"{cls.__module__}.{cls.__qualname__}",
        "available": cls.is_available() if hasattr(cls, "is_available") else None,
        "license": getattr(cls, "license", None),
        "requires_gpu": getattr(cls, "requires_gpu", False),
        "formats": cls.supported_formats() if hasattr(cls, "supported_formats") else None,
    }
