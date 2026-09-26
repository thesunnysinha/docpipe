"""Plugin allowlists and availability checks."""

from __future__ import annotations

import contextvars
import json
from typing import Any

from fastapi import HTTPException

from docpipe.config import get_settings
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.policy import PluginPolicy
from docpipe.profiles.audit import log_plugin_denied
from docpipe.profiles.catalog import CHUNKER_TIERS, PARSER_TIERS, RERANKER_TIERS
from docpipe.registry.registry import PluginRegistry

_TENANT_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "docpipe_tenant", default=None
)
_SETTINGS_CONTEXT: contextvars.ContextVar[DocpipeSettings | None] = contextvars.ContextVar(
    "docpipe_request_settings", default=None
)


def _parse_csv(value: str | None) -> list[str] | None:
    if not value or not value.strip():
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def set_tenant_context(
    tenant_id: str | None,
    *,
    settings: DocpipeSettings | None = None,
) -> tuple[contextvars.Token[str | None], contextvars.Token[DocpipeSettings | None]]:
    """Bind verified tenant identity and application settings for one request."""
    return _TENANT_CONTEXT.set(tenant_id), _SETTINGS_CONTEXT.set(settings)


def reset_tenant_context(
    tokens: tuple[contextvars.Token[str | None], contextvars.Token[DocpipeSettings | None]],
) -> None:
    """Restore the prior request identity and settings context."""
    tenant_token, settings_token = tokens
    _SETTINGS_CONTEXT.reset(settings_token)
    _TENANT_CONTEXT.reset(tenant_token)


def get_tenant_context() -> str | None:
    """Return the verified tenant identity bound to the current context, if any."""
    return _TENANT_CONTEXT.get()


def _current_settings() -> DocpipeSettings:
    return _SETTINGS_CONTEXT.get() or get_settings()


def catalog_tenant_policy(settings: DocpipeSettings, tenant_id: str | None) -> PluginPolicy | None:
    """Build a request-local policy, denying all tenants when identity is absent."""
    if not settings.tenant_plugin_policies:
        return None
    try:
        policies = json.loads(settings.tenant_plugin_policies)
    except json.JSONDecodeError:
        policies = {}
    if not isinstance(policies, dict):
        policies = {}
    selected = policies.get(tenant_id) if tenant_id is not None else None
    if not isinstance(selected, dict):
        # A configured tenant boundary must never silently fall back to the
        # process-wide allowlist for an unknown or unauthenticated tenant.
        return PluginPolicy.create(
            allowlists={
                PluginCategory.SOURCE: set(),
                PluginCategory.VECTORSTORE: set(),
            }
        )
    allowlists: dict[PluginCategory, set[str]] = {}
    for category, key in (
        (PluginCategory.SOURCE, "enabled_sources"),
        (PluginCategory.VECTORSTORE, "enabled_vectorstores"),
    ):
        raw = selected.get(key)
        if isinstance(raw, str):
            allowlists[category] = set(_parse_csv(raw) or ())
        elif key in selected:
            allowlists[category] = set()
    return PluginPolicy.create(allowlists=allowlists)


def _tenant_policies() -> dict[str, dict[str, str]]:
    raw = _current_settings().tenant_plugin_policies
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        tenant: policy
        for tenant, policy in data.items()
        if isinstance(tenant, str)
        and isinstance(policy, dict)
        and all(isinstance(key, str) and isinstance(value, str) for key, value in policy.items())
    }


def enabled_plugins(group: str) -> list[str] | None:
    """Return allowlist for a plugin group, or None for all installed."""
    tenant = get_tenant_context()
    policies = _tenant_policies()
    settings = _current_settings()
    if settings.tenant_plugin_policies and (tenant is None or tenant not in policies):
        return []
    if tenant:
        policy = policies.get(tenant, {})
        tenant_key = f"enabled_{group}"
        if tenant_key in policy:
            return _parse_csv(policy[tenant_key])

    attr = f"enabled_{group}"
    raw = getattr(settings, attr, None)
    return _parse_csv(raw)


def disabled_plugins() -> set[str]:
    """Return globally disabled plugin names from the active request settings."""
    settings = _current_settings()
    return set(_parse_csv(settings.disabled_plugins) or [])


def is_plugin_allowed(group: str, name: str) -> bool:
    """Check a plugin against global disables and the effective allowlist.

    Tenant-scoped policy takes precedence when configured; an absent or unknown
    tenant then receives no tenant-scoped plugins rather than the global list.
    """
    if name in disabled_plugins():
        return False
    allow = enabled_plugins(group)
    if allow is None:
        return True
    return name in allow


def assert_plugin_allowed(group: str, name: str) -> None:
    """Validate registration, policy, and dependency availability for a plugin.

    Raises :class:`ConfigurationError` for unknown, disabled, or unavailable
    plugins. A policy denial also records a metric and audit event.
    """
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
    """Convert a client-facing plugin configuration error into HTTP 422."""
    return HTTPException(status_code=422, detail=str(exc))


def enrich_plugin_info(group: str, name: str, info: dict[str, Any]) -> dict[str, Any]:
    """Copy plugin metadata and add its catalog tier and current allow status."""
    tier_maps = {
        "parsers": PARSER_TIERS,
        "chunkers": CHUNKER_TIERS,
        "rerankers": RERANKER_TIERS,
    }
    enriched = dict(info)
    enriched["tier"] = tier_maps.get(group, {}).get(name)
    enriched["allowed"] = is_plugin_allowed(group, name)
    return enriched


def build_plugins_payload(
    registry: PluginRegistry | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Return legacy plugin groups while allowing runtime-owned registry injection."""
    registry = registry or PluginRegistry.get()
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
