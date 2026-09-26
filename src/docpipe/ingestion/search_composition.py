"""Assemble search from a policy-selected vector plugin and embedding port."""

from __future__ import annotations

from typing import cast

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig
from docpipe.embeddings.langchain_adapter import (
    LangChainEmbeddingAdapter,
    LangChainEmbeddingsLike,
)
from docpipe.ingestion.composition import VectorStorePlugin, _vector_plugin_config
from docpipe.ingestion.search import SearchCoordinator
from docpipe.plugins.contracts.vectorstore import CollectionRef, VectorCapability
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.lifecycle import PluginScopeHandle


async def build_search_coordinator(
    config: IngestionConfig,
    *,
    runtime: DocpipeRuntime,
    scope: PluginScopeHandle,
    embeddings: object,
) -> SearchCoordinator:
    """Select and own the requested reader for a single search operation."""
    if not runtime.is_active:
        raise RuntimeError("search requires an active Docpipe runtime")
    provider = (
        config.vector_store.provider if config.vector_store else config.vector_backend or "pgvector"
    )
    loaded = runtime.load_plugin(PluginCategory.VECTORSTORE, provider)
    instance = await scope.acquire(
        f"search.vectorstore.{provider}",
        lambda: loaded.create(
            _vector_plugin_config(config, provider), context=runtime.factory_context()
        ),
    )
    if not isinstance(instance, VectorStorePlugin):
        raise ConfigurationError("selected vector plugin returned an invalid binding")
    binding = instance.binding
    if binding.reader is None or VectorCapability.DENSE_SEARCH not in binding.capabilities:
        raise ConfigurationError("selected vector plugin lacks dense search capability")
    return SearchCoordinator(
        reader=binding.reader,
        encoder=LangChainEmbeddingAdapter(
            cast(LangChainEmbeddingsLike, embeddings), runtime.blocking_runner
        ),
        collection=CollectionRef(config.table_name),
        capabilities=binding.capabilities,
    )
