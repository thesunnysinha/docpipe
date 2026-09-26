"""Bounded health probe for the single configured vector plugin."""

from __future__ import annotations

import asyncio
import logging
import time

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.compatibility import resolve_vector_options
from docpipe.plugins.contracts.vectorstore import VectorStoreBinding
from docpipe.plugins.descriptors import PluginCategory
from docpipe.schemas.health import DependencyStatus

_LOGGER = logging.getLogger(__name__)


async def probe_selected_vector(
    runtime: DocpipeRuntime, *, timeout_seconds: float = 3.0
) -> DependencyStatus:
    """Probe only the configured provider through its advertised health facet.

    Callers must invoke this explicitly; the shallow ``/health`` endpoint does
    not import or initialize optional plugins. Error details are deliberately
    value-free so credentials and vendor URLs cannot reach public responses.
    """
    settings = runtime.settings
    selected = resolve_vector_options(
        provider=settings.vector_backend,
        connection_string=settings.db_connection_string,
        collection=settings.db_table_name,
        index_root=str(settings.turbovec_index_dir),
        bit_width=settings.turbovec_bit_width,
        namespaced=settings.vector_store,
        explicit_legacy=settings.model_fields_set,
    )
    name = f"vectorstore:{selected.provider}"
    if selected.provider == "pgvector" and "dsn" not in selected.options:
        return DependencyStatus(name=name, status="degraded", detail="vector plugin not configured")
    started = time.perf_counter()
    _LOGGER.info(
        "plugin.health.started",
        extra={"event": "plugin.health.started", "plugin": selected.provider},
    )
    try:
        async with runtime.plugin_runtime.request_scope() as scope:
            loaded = runtime.load_plugin(PluginCategory.VECTORSTORE, selected.provider)
            instance = await scope.acquire(
                f"health.vectorstore.{selected.provider}",
                lambda: loaded.create(selected, context=runtime.factory_context()),
            )
            binding = getattr(instance, "binding", None)
            if not isinstance(binding, VectorStoreBinding) or binding.health is None:
                return DependencyStatus(
                    name=name,
                    status="degraded",
                    detail="vector plugin has no health facet",
                )
            healthy = await asyncio.wait_for(binding.health.health(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        detail = "vector plugin probe timed out"
    except Exception as error:  # noqa: BLE001
        _LOGGER.warning(
            "plugin.health.failed",
            extra={
                "event": "plugin.health.failed",
                "plugin": selected.provider,
                "error_type": type(error).__name__,
            },
        )
        detail = "vector plugin probe failed"
    else:
        _LOGGER.info(
            "plugin.health.completed",
            extra={
                "event": "plugin.health.completed",
                "plugin": selected.provider,
                "healthy": healthy,
            },
        )
        return DependencyStatus(
            name=name,
            status="ok" if healthy else "unavailable",
            latency_ms=(time.perf_counter() - started) * 1000,
            detail=None if healthy else "vector plugin reported unhealthy",
        )
    return DependencyStatus(
        name=name,
        status="unavailable",
        latency_ms=(time.perf_counter() - started) * 1000,
        detail=detail,
    )
