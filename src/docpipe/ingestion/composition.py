"""Application composition for ingestion over selected vector-store facets."""

from __future__ import annotations

from typing import Protocol, cast, runtime_checkable

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.compatibility import resolve_vector_options
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import IngestionConfig
from docpipe.embeddings.langchain_adapter import (
    LangChainEmbeddingAdapter,
    LangChainEmbeddingsLike,
)
from docpipe.ingestion.configuration import (
    IncrementalFailureMode,
    IngestionOptions,
    IngestMode,
)
from docpipe.ingestion.contextualization import Contextualizer
from docpipe.ingestion.coordinator import IngestionCoordinator
from docpipe.ingestion.document_builder import DocumentBuilder
from docpipe.ingestion.incremental import IncrementalDecider, VectorIncrementalState
from docpipe.ingestion.legacy import LangChainChunkerAdapter, LegacyChunker
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    VectorCapability,
    VectorStoreBinding,
)
from docpipe.plugins.descriptors import PluginCategory


@runtime_checkable
class VectorStorePlugin(Protocol):
    """Selected vector plugin surface consumed by application composition."""

    @property
    def binding(self) -> VectorStoreBinding:
        """Return supported vector facets."""
        ...


def build_ingestion_coordinator(
    config: IngestionConfig,
    *,
    runtime: DocpipeRuntime,
    embeddings: object,
    chunker: object,
    contextualizer: Contextualizer | None = None,
) -> IngestionCoordinator:
    """Select a vector plugin and assemble one vendor-neutral coordinator."""
    if not runtime.is_active:
        raise RuntimeError("ingestion requires an active Docpipe runtime")
    provider = (
        config.vector_store.provider if config.vector_store else config.vector_backend or "pgvector"
    )
    loaded = runtime.load_plugin(PluginCategory.VECTORSTORE, provider)
    instance = loaded.create(
        _vector_plugin_config(config, provider),
        context=runtime.factory_context(),
    )
    if not isinstance(instance, VectorStorePlugin):
        raise ConfigurationError("selected vector plugin returned an invalid binding")
    binding = instance.binding
    _require_ingestion_facets(binding)
    if binding.writer is None or binding.admin is None:
        raise ConfigurationError("selected vector plugin cannot ingest records")

    encoder = LangChainEmbeddingAdapter(
        cast(LangChainEmbeddingsLike, embeddings),
        runtime.blocking_runner,
    )
    options = IngestionOptions(
        collection=CollectionRef(config.table_name),
        batch_size=config.write_batch_size,
        max_in_flight=config.max_in_flight,
        incremental=config.incremental,
        incremental_failure_mode=IncrementalFailureMode(config.incremental_failure_mode),
        chunk_metadata=config.chunk_metadata,
    )
    incremental_decider = _incremental_decider(binding, encoder, options)
    return IngestionCoordinator(
        options=options,
        builder=DocumentBuilder(IngestMode(config.ingest_mode)),
        chunker=LangChainChunkerAdapter(
            cast(LegacyChunker, chunker),
            runtime.blocking_runner,
        ),
        encoder=encoder,
        writer=binding.writer,
        admin=binding.admin,
        incremental_decider=incremental_decider,
        contextualizer=contextualizer,
    )


def _vector_plugin_config(config: IngestionConfig, provider: str) -> PluginConfig:
    resolved = resolve_vector_options(
        provider=config.vector_backend,
        connection_string=config.connection_string,
        collection=config.table_name,
        index_root=config.turbovec_index_dir,
        bit_width=config.turbovec_bit_width,
        namespaced=config.vector_store,
        explicit_legacy=config.model_fields_set,
    )
    if resolved.provider != provider:
        raise ConfigurationError("selected vector provider does not match vector_store")
    return resolved


def _require_ingestion_facets(binding: VectorStoreBinding) -> None:
    required = {VectorCapability.UPSERT, VectorCapability.COLLECTION_ADMIN}
    missing = required - binding.capabilities
    if missing:
        names = ", ".join(sorted(capability.value for capability in missing))
        raise ConfigurationError(f"selected vector plugin lacks ingestion capabilities: {names}")


def _incremental_decider(
    binding: VectorStoreBinding,
    encoder: LangChainEmbeddingAdapter,
    options: IngestionOptions,
) -> IncrementalDecider | None:
    if not options.incremental:
        return None
    if binding.reader is None or VectorCapability.METADATA_FILTER not in binding.capabilities:
        return None
    return IncrementalDecider(
        VectorIncrementalState(binding.reader, encoder, options.collection),
        failure_mode=options.incremental_failure_mode,
    )
