"""Apply runtime presets to API requests."""

from __future__ import annotations

from typing import Any

from docpipe.config import get_settings
from docpipe.profiles.catalog import RUNTIME_PRESETS
from docpipe.profiles.guardrails import assert_plugin_allowed


def apply_defaults_and_preset(
    fields: dict[str, Any],
    *,
    preset: str | None,
    applicable: set[str],
    explicit: set[str] | None = None,
) -> dict[str, Any]:
    """Merge server defaults, optional preset, then explicit request fields."""
    settings = get_settings()
    resolved = dict(fields)
    explicit_keys = explicit or set()

    default_map = {
        "parser": settings.default_parser,
        "tier": settings.default_parser_tier,
        "chunker": settings.default_chunker,
        "reranker": settings.default_reranker,
        "extractor": settings.default_extractor,
        "evaluator": settings.default_evaluator,
        "strategy": settings.default_rag_strategy,
        "agent_backend": settings.default_agent_backend,
    }
    for key, value in default_map.items():
        if key not in applicable:
            continue
        if key in explicit_keys:
            continue
        if resolved.get(key) in (None, ""):
            resolved[key] = value

    if preset:
        if preset not in RUNTIME_PRESETS:
            raise ValueError(
                f"Unknown preset '{preset}'. Available: {list(RUNTIME_PRESETS.keys())}"
            )
        for key, value in RUNTIME_PRESETS[preset].items():
            if key == "description":
                continue
            if key not in applicable:
                continue
            if key in explicit_keys:
                continue
            resolved[key] = value

    return resolved


def validate_resolved_plugins(resolved: dict[str, Any]) -> None:
    checks: list[tuple[str, str]] = []
    if (parser := resolved.get("parser")) and parser != "auto":
        checks.append(("parsers", parser))
    if chunker := resolved.get("chunker"):
        checks.append(("chunkers", chunker))
    if (reranker := resolved.get("reranker")) and reranker != "none":
        checks.append(("rerankers", reranker))
    if extractor := resolved.get("extractor"):
        checks.append(("extractors", extractor))
    if evaluator := resolved.get("evaluator"):
        checks.append(("evaluators", evaluator))
    for group, name in checks:
        assert_plugin_allowed(group, name)


def list_runtime_presets() -> dict[str, dict[str, Any]]:
    settings = get_settings()
    out: dict[str, dict[str, Any]] = {}
    for name, spec in RUNTIME_PRESETS.items():
        out[name] = {
            "description": spec["description"],
            "fields": {k: v for k, v in spec.items() if k != "description"},
            "server_default": name == settings.default_runtime_preset,
        }
    return out
