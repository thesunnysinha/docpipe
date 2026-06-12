"""Parser auto-selection by tier and file extension."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from docpipe.registry.registry import PluginRegistry

TIER_PARSERS: dict[str, list[str]] = {
    "fast": ["markitdown", "pymupdf"],
    "balanced": ["docling"],
    "quality": ["mineru", "paddleocr", "glm-ocr", "docling"],
}

_EXTENSION_HINTS: dict[str, list[str]] = {
    ".pdf": ["pymupdf", "docling", "mineru", "markitdown"],
    ".docx": ["markitdown", "docling", "unstructured"],
    ".pptx": ["markitdown", "docling", "unstructured"],
    ".xlsx": ["markitdown", "docling"],
    ".html": ["markitdown", "docling"],
    ".htm": ["markitdown", "docling"],
    ".png": ["glm-ocr", "docling"],
    ".jpg": ["glm-ocr", "docling"],
    ".jpeg": ["glm-ocr", "docling"],
}


def _suffix(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return Path(urlparse(source).path).suffix.lower()
    return Path(source).suffix.lower()


def resolve_parser(
    name: str,
    *,
    tier: str = "balanced",
    source: str | None = None,
) -> str:
    """Resolve parser name; supports ``auto`` with optional source hint."""
    if name != "auto":
        return name

    registry = PluginRegistry.get()
    candidates = list(TIER_PARSERS.get(tier, TIER_PARSERS["balanced"]))
    if source:
        ext = _suffix(source)
        hinted = _EXTENSION_HINTS.get(ext, [])
        candidates = hinted + [c for c in candidates if c not in hinted]

    for candidate in candidates:
        if candidate not in registry.list_parsers():
            continue
        info = registry.parser_info(candidate)
        if info.get("available"):
            return candidate
    available = [p for p in registry.list_parsers() if registry.parser_info(p).get("available")]
    if not available:
        raise ValueError("No parsers available")
    return available[0]
