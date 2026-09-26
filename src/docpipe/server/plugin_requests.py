"""Resolve presets and guardrails for API requests."""

from __future__ import annotations

from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.profiles.guardrails import assert_plugin_allowed, http_exception_for_config
from docpipe.profiles.presets import apply_defaults_and_preset, validate_resolved_plugins


def resolve_fields(
    fields: dict[str, Any],
    *,
    preset: str | None,
    applicable: set[str],
    explicit: set[str] | None = None,
    endpoint: str | None = None,
) -> dict[str, Any]:
    """Apply request defaults/preset and enforce resolved plugin policies.

    Configuration failures are converted to the server's structured HTTP
    mapping; value-validation failures become HTTP 422. Preset usage metrics
    are recorded only after successful resolution and only when an endpoint
    label is supplied.
    """
    try:
        resolved = apply_defaults_and_preset(
            fields,
            preset=preset,
            applicable=applicable,
            explicit=explicit,
        )
        validate_resolved_plugins(resolved)
        if preset and endpoint:
            from docpipe.observability.metrics import record_preset_usage

            record_preset_usage(preset, endpoint)
        return resolved
    except ConfigurationError as exc:
        raise http_exception_for_config(exc) from exc
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=str(exc)) from exc


def resolve_parser_name(resolved: dict[str, Any], source: str) -> str:
    """Select a parser for the resolved tier and source, then enforce policy.

    Parser routing and the guardrail check happen here so callers cannot use a
    parser selected by automatic resolution without checking plugin policy.
    """
    from docpipe.parsers.router import resolve_parser

    parser = str(resolved.get("parser", "auto"))
    tier = str(resolved.get("tier", "balanced"))
    name = resolve_parser(parser, tier=tier, source=source)
    assert_plugin_allowed("parsers", name)
    return name
