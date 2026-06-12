"""Recommend plugins for a document source and goal."""

from __future__ import annotations

from docpipe.parsers.router import resolve_parser
from docpipe.profiles.catalog import RUNTIME_PRESETS
from docpipe.profiles.guardrails import build_plugins_payload, is_plugin_allowed
from docpipe.profiles.presets import apply_defaults_and_preset


def resolve_recommendation(
    *,
    source: str | None = None,
    goal: str = "ingest",
    preset: str | None = None,
) -> dict[str, object]:
    """Return recommended parser/chunker/reranker for a source and goal."""
    applicable = {"parser", "tier", "chunker", "reranker", "strategy"}
    if goal == "rag":
        applicable.add("strategy")
    if goal == "agents":
        applicable.update({"agent_backend", "enable_parse_tool", "strategy"})

    base: dict[str, object] = {}
    resolved = apply_defaults_and_preset(base, preset=preset, applicable=applicable)

    parser = str(resolved.get("parser", "auto"))
    tier = str(resolved.get("tier", "balanced"))
    parser_name = resolve_parser(parser, tier=tier, source=source)

    # Pick first allowed chunker/reranker from preset or defaults
    for group, key in (("chunkers", "chunker"), ("rerankers", "reranker")):
        candidate = str(resolved.get(key, ""))
        if candidate and candidate != "none" and is_plugin_allowed(group, candidate):
            continue
        plugins = build_plugins_payload().get(group, {})
        for name, info in plugins.items():
            if info.get("available") and info.get("allowed"):
                resolved[key] = name
                break

    return {
        "source": source,
        "goal": goal,
        "preset": preset,
        "recommended": {
            "parser": parser_name,
            "tier": tier,
            "chunker": resolved.get("chunker"),
            "reranker": resolved.get("reranker"),
            "strategy": resolved.get("strategy"),
        },
        "preset_catalog": {k: v["description"] for k, v in RUNTIME_PRESETS.items()},
    }
