"""Pure legacy field translation and bounded deprecation notices."""

from __future__ import annotations

import threading
import warnings
from collections.abc import Collection
from pathlib import Path

from pydantic import JsonValue

from docpipe.config.plugin_options import SourcePluginOptions, VectorStoreOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError

_WARNED_FIELDS: set[str] = set()
_WARNING_LOCK = threading.Lock()


def resolve_vector_options(
    *,
    provider: str | None,
    connection_string: str | None,
    collection: str,
    index_root: str | None = None,
    bit_width: int = 4,
    namespaced: VectorStoreOptions | None = None,
    explicit_legacy: Collection[str] = (),
) -> VectorStoreOptions:
    """Merge legacy vector fields with an optional selected provider envelope.

    Explicit conflicting legacy fields raise field-specific errors. Otherwise
    the namespaced provider and its option values take precedence.
    """
    explicit = frozenset(explicit_legacy)
    if (
        namespaced is not None
        and provider is not None
        and "vector_backend" in explicit
        and provider != namespaced.provider
    ):
        raise ConfigurationError("vector_backend conflicts with vector_store.provider")

    selected = namespaced.provider if namespaced is not None else provider or "pgvector"
    legacy = _legacy_vector_options(
        selected,
        connection_string=connection_string,
        collection=collection,
        index_root=index_root,
        bit_width=bit_width,
    )
    overrides = namespaced.options if namespaced is not None else {}
    _reject_conflicts(
        legacy,
        overrides,
        explicit,
        {
            "dsn": "connection_string",
            "collection": "table_name",
            "index_root": "turbovec_index_dir",
            "bit_width": "turbovec_bit_width",
        },
    )
    return VectorStoreOptions(provider=selected, options={**legacy, **overrides})


def _legacy_vector_options(
    provider: str,
    *,
    connection_string: str | None,
    collection: str,
    index_root: str | None,
    bit_width: int,
) -> dict[str, JsonValue]:
    if provider == "pgvector":
        options: dict[str, JsonValue] = {"collection": collection}
        if connection_string is not None:
            options["dsn"] = connection_string
        return options
    if provider == "turbovec":
        return {
            "index_root": index_root or ".docpipe/indices",
            "collection": collection,
            "bit_width": bit_width,
        }
    return {"collection": collection}


def resolve_source_options(
    provider: str,
    settings: DocpipeSettings,
    *,
    temporary_root: str | Path | None = None,
    namespaced: SourcePluginOptions | None = None,
) -> SourcePluginOptions:
    """Merge trusted source defaults with selected provider options."""
    if namespaced is not None and namespaced.provider != provider:
        raise ConfigurationError("source_plugin.provider conflicts with source URI scheme")
    legacy = _legacy_source_options(provider, settings, temporary_root=temporary_root)
    configured = settings.source_plugin_options.get(provider, {})
    overrides = namespaced.options if namespaced is not None else {}
    if provider == "s3":
        # Buckets, endpoints, credentials, and artifact roots are process-owned.
        # Request envelopes select S3; they must not establish its trust policy.
        for option, value in overrides.items():
            if option not in configured or configured[option] != value:
                raise ConfigurationError(f"S3 source option '{option}' is operator-owned")
    mapping = {
        "allowed_roots": "source_allowed_roots",
        "temporary_root": "source_temporary_root",
        "max_bytes": "source_max_bytes",
        "chunk_bytes": "source_chunk_bytes",
        "total_timeout": "source_http_timeout_seconds",
        "max_redirects": "source_http_max_redirects",
        "allow_private": "allow_private_urls",
        "allowed_ports": "source_http_allowed_ports",
    }
    _reject_conflicts(legacy, configured, settings.model_fields_set, mapping)
    # Request-provided options may narrow a third-party source plugin, but
    # built-in local/HTTP security limits remain operator-owned.
    _reject_conflicts(legacy, overrides, frozenset(mapping.values()), mapping)
    return SourcePluginOptions(provider=provider, options={**legacy, **configured, **overrides})


def _legacy_source_options(
    provider: str,
    settings: DocpipeSettings,
    *,
    temporary_root: str | Path | None,
) -> dict[str, JsonValue]:
    common: dict[str, JsonValue] = {
        "max_bytes": settings.source_max_bytes,
        "chunk_bytes": settings.source_chunk_bytes,
    }
    if provider == "local":
        return {
            **common,
            "allowed_roots": [str(path) for path in settings.source_allowed_roots],
        }
    if provider == "http":
        return {
            **common,
            "temporary_root": str(temporary_root or settings.source_temporary_root),
            "total_timeout": settings.source_http_timeout_seconds,
            "max_redirects": settings.source_http_max_redirects,
            "allow_private": settings.allow_private_urls,
            "allowed_ports": list(settings.source_http_allowed_ports),
        }
    return {}


def _reject_conflicts(
    legacy: dict[str, JsonValue],
    overrides: dict[str, JsonValue],
    explicit: Collection[str],
    field_names: dict[str, str],
) -> None:
    for option, value in overrides.items():
        legacy_field = field_names.get(option)
        if legacy_field in explicit and option in legacy and legacy[option] != value:
            raise ConfigurationError(f"{legacy_field} conflicts with namespaced option '{option}'")


def warn_legacy_field_once(field: str) -> None:
    """Emit at most one value-free deprecation notice per legacy field."""
    with _WARNING_LOCK:
        if field in _WARNED_FIELDS:
            return
        _WARNED_FIELDS.add(field)
    warnings.warn(
        f"{field} is deprecated; use namespaced plugin options",
        DeprecationWarning,
        stacklevel=2,
    )
