"""Collection operations through capability-negotiated vector plugin facets."""

from __future__ import annotations

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.core.errors import ConfigurationError
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorCapability,
    VectorStoreBinding,
)
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.errors import PluginCapabilityError
from docpipe.plugins.lifecycle import PluginScopeHandle
from docpipe.schemas.delete import DeleteRequest
from docpipe.schemas.sources import ListSourcesRequest


def validate_plugin_delete(request: DeleteRequest) -> None:
    """Reject legacy substring deletion that the exact-source facet cannot express."""
    if request.match_mode != "exact":
        raise ConfigurationError("selected vector plugin supports exact source deletion only")


def validate_plugin_list(request: ListSourcesRequest) -> None:
    """Reject filters that source aggregation does not model yet."""
    if request.filters:
        raise ConfigurationError(
            "selected vector plugin source aggregation does not support filters"
        )


async def delete_selected_source(
    runtime: DocpipeRuntime,
    options: VectorStoreOptions,
    request: DeleteRequest,
) -> int:
    """Delete one exact source through the selected writer facet."""
    validate_plugin_delete(request)
    assert request.source is not None
    async with runtime.plugin_runtime.request_scope() as scope:
        binding = await _selected_binding(runtime, scope, options)
        if VectorCapability.DELETE_BY_SOURCE not in binding.capabilities or binding.writer is None:
            raise PluginCapabilityError(
                "Selected vector plugin does not support delete by source",
                context={"required_capability": VectorCapability.DELETE_BY_SOURCE.value},
            )
        return await binding.writer.delete_by_source(
            CollectionRef(request.table_name), request.source
        )


async def list_selected_sources(
    runtime: DocpipeRuntime,
    options: VectorStoreOptions,
    request: ListSourcesRequest,
) -> tuple[SourceAggregate, ...]:
    """Aggregate sources through the selected reader facet."""
    validate_plugin_list(request)
    async with runtime.plugin_runtime.request_scope() as scope:
        binding = await _selected_binding(runtime, scope, options)
        if (
            VectorCapability.SOURCE_AGGREGATION not in binding.capabilities
            or binding.reader is None
        ):
            raise PluginCapabilityError(
                "Selected vector plugin does not support source aggregation",
                context={"required_capability": VectorCapability.SOURCE_AGGREGATION.value},
            )
        return await binding.reader.aggregate_sources(CollectionRef(request.table_name))


async def _selected_binding(
    runtime: DocpipeRuntime, scope: PluginScopeHandle, options: VectorStoreOptions
) -> VectorStoreBinding:
    """Acquire one operation-owned plugin after catalog and policy selection."""
    loaded = runtime.load_plugin(PluginCategory.VECTORSTORE, options.provider)
    instance = await scope.acquire(
        f"collection.vectorstore.{options.provider}",
        lambda: loaded.create(options, context=runtime.factory_context()),
    )
    binding = getattr(instance, "binding", None)
    if not isinstance(binding, VectorStoreBinding):
        raise ConfigurationError("selected vector plugin returned an invalid binding")
    return binding
