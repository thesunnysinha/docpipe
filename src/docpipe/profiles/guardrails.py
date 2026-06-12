"""Plugin allowlists and availability checks."""

from __future__ import annotations

import contextvars
import json
from typing import Any

from fastapi import HTTPException

from docpipe.config import get_settings
from docpipe.core.errors import ConfigurationError
from docpipe.profiles.audit import log_plugin_denied
from docpipe.profiles.catalog import CHUNKER_TIERS, PARSER_TIERS, RERANKER_TIERS
from docpipe.registry.registry import PluginRegistry

_TENANT_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "docpipe_tenant", default=None
)


def _parse_csv(value: str | None) -> list[str] | None:
    if not value or not value.strip():
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def set_tenant_context(tenant_id: str | None) -> contextvars.Token[str | None]:
    """Bind tenant id for the current request (from X-Docpipe-Tenant-Id)."""
    return _TENANT_CONTEXT.set(tenant_id)


def reset_tenant_context(token: contextvars.Token[str | None]) -> None:
    _TENANT_CONTEXT.reset(token)


def get_tenant_context() -> str | None:
    return _TENANT_CONTEXT.get()


def _tenant_policies() -> dict[str, dict[str, str]]:
    raw = get_settings().tenant_plugin_policies
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def enabled_plugins(group: str) -> list[str] | None:
    """Return allowlist for a plugin group, or None for all installed."""
    tenant = get_tenant_context()
    if tenant:
        policy = _tenant_policies().get(tenant, {})
        tenant_key = f"enabled_{group}"
        if tenant_key in policy:
            return _parse_csv(policy[tenant_key])

    settings = get_settings()
    attr = f"enabled_{group}"
    raw = getattr(settings, attr, None)
    return _parse_csv(raw)


def disabled_plugins() -> set[str]:
    settings = get_settings()
    return set(_parse_csv(settings.disabled_plugins) or [])


def is_plugin_allowed(group: str, name: str) -> bool:
    if name in disabled_plugins():
        return False
    allow = enabled_plugins(group)
    if allow is None:
        return True
    return name in allow


def assert_plugin_allowed(group: str, name: str) -> None:
    registry = PluginRegistry.get()
    if name not in getattr(registry, f"list_{group}")():
        raise ConfigurationError(
            f"Unknown {group[:-1]} '{name}'. Available: {getattr(registry, f'list_{group}')()}"
        )
    if not is_plugin_allowed(group, name):
        from docpipe.observability.metrics import record_plugin_denied

        record_plugin_denied(group, name)
        log_plugin_denied(group=group, name=name, tenant=get_tenant_context())
        raise ConfigurationError(
            f"{group[:-1].title()} '{name}' is disabled on this server. "
            f"Check DOCPIPE_ENABLED_{group.upper()} / DOCPIPE_DISABLED_PLUGINS."
        )
    info_method = getattr(registry, f"{group[:-1]}_info")
    info = info_method(name)
    if info.get("available") is False:
        raise ConfigurationError(
            f"{group[:-1].title()} '{name}' is registered but not installed. "
            f"Install the required extra or use a different {group[:-1]}."
        )


def http_exception_for_config(exc: ConfigurationError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


def enrich_plugin_info(group: str, name: str, info: dict[str, Any]) -> dict[str, Any]:
    tier_maps = {
        "parsers": PARSER_TIERS,
        "chunkers": CHUNKER_TIERS,
        "rerankers": RERANKER_TIERS,
    }
    enriched = dict(info)
    enriched["tier"] = tier_maps.get(group, {}).get(name)
    enriched["allowed"] = is_plugin_allowed(group, name)
    return enriched


def build_plugins_payload() -> dict[str, dict[str, dict[str, Any]]]:
    registry = PluginRegistry.get()
    payload: dict[str, dict[str, dict[str, Any]]] = {}
    for group, list_method, info_method in (
        ("parsers", registry.list_parsers, registry.parser_info),
        ("extractors", registry.list_extractors, registry.extractor_info),
        ("chunkers", registry.list_chunkers, registry.chunker_info),
        ("rerankers", registry.list_rerankers, registry.reranker_info),
        ("evaluators", registry.list_evaluators, registry.evaluator_info),
    ):
        payload[group] = {
            name: enrich_plugin_info(group, name, info_method(name)) for name in list_method()
        }
    return payload
