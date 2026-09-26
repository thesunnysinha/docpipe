"""Select a parser by explicit name or installed-parser hints.

Automatic selection first applies a tier-specific candidate list, then moves
file-extension hints to the front when a source is provided. Candidates are
skipped unless registered and available; if none of the preferred candidates
qualify, the first available parser in registry order is used. This module only
selects a parser name: it does not parse content or validate an explicit name.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

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
    parsed = urlsplit(source)
    candidate = parsed.path if parsed.scheme else source
    return Path(candidate).suffix.lower()


def resolve_parser(
    name: str,
    *,
    tier: str = "balanced",
    source: str | None = None,
) -> str:
    """Resolve an explicit parser name or choose an available parser.

    Explicit names are returned unchanged; validation and availability checks
    are left to the caller or registry lookup. For ``"auto"``, candidates
    start with the selected tier (unknown tiers use ``"balanced"``). If a
    source is supplied, its path suffix is used to prioritize extension hints
    ahead of tier candidates. The first registered and available candidate
    wins. If no preferred candidate is usable, selection falls back to the
    first available registered parser, preserving registry order.

    Args:
        name: Explicit parser identifier or ``"auto"``.
        tier: Candidate quality/speed tier used only for automatic selection.
            Unknown values behave like ``"balanced"``.
        source: Optional path or URL used only to infer an extension hint; the
            URL query and fragment do not participate in suffix detection.

    Returns:
        The explicit name unchanged, or the selected available parser name.

    Raises:
        ValueError: If automatic selection is requested and the registry has
            no available parser.
    """
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
