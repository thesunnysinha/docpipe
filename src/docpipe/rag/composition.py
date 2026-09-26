"""RAG composition over explicitly selected vector and model ports."""

from __future__ import annotations

from typing import Any, Protocol, cast, runtime_checkable

from docpipe.bootstrap.runtime import DocpipeRuntime
from docpipe.config.compatibility import resolve_vector_options
from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk, RAGConfig
from docpipe.embeddings.langchain_adapter import (
    LangChainEmbeddingAdapter,
    LangChainEmbeddingsLike,
)
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import (
    And,
    CollectionRef,
    Equals,
    FilterExpression,
    VectorCapability,
    VectorStoreBinding,
)
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.lifecycle import PluginScopeHandle
from docpipe.rag.coordinator import RAGCoordinator, RAGOptions
from docpipe.rag.generation import LangChainAnswerGenerator, normalize_content
from docpipe.rag.retrieval.automatic import AutomaticStrategy
from docpipe.rag.retrieval.base import RetrievalStrategy, TextRewriter, VectorSearch
from docpipe.rag.retrieval.hybrid import HybridStrategy
from docpipe.rag.retrieval.hyde import HydeStrategy
from docpipe.rag.retrieval.lightrag import LightRAGStrategy, graph_query_adapter
from docpipe.rag.retrieval.multi_query import MultiQueryStrategy
from docpipe.rag.retrieval.naive import NaiveStrategy
from docpipe.rag.retrieval.parent_document import ParentDocumentStrategy
from docpipe.rag.retrieval.registry import StrategyRegistry


@runtime_checkable
class VectorStorePlugin(Protocol):
    """Narrow facet surface required from a selected vector plugin."""

    @property
    def binding(self) -> VectorStoreBinding:
        """Return the plugin's advertised vector capabilities."""
        ...


class ModelTextRewriter:
    """Adapt a synchronous LLM to the asynchronous query-rewriting port."""

    def __init__(self, llm: Any, runtime: DocpipeRuntime) -> None:
        self._llm = llm
        self._runner = runtime.blocking_runner

    async def complete(self, prompt: str) -> str:
        """Return model text after bounded blocking execution."""
        from langchain_core.messages import HumanMessage

        response = await self._runner.run(self._llm.invoke, [HumanMessage(content=prompt)])
        return normalize_content(response.content)


class LegacyRerankerAdapter:
    """Contain legacy plugin registry access within application composition."""

    def __init__(self, runtime: DocpipeRuntime, name: str, model: str | None) -> None:
        self._runtime = runtime
        self._name = name
        self._model = model

    async def rerank(
        self, question: str, chunks: tuple[RAGChunk, ...], *, top_n: int
    ) -> tuple[RAGChunk, ...]:
        """Rerank with a selected legacy adapter behind a bounded executor."""
        try:
            plugin = self._runtime.legacy_registry.get_reranker(self._name, model=self._model)
        except Exception as error:
            raise RAGError(f"Reranker '{self._name}' is unavailable") from error

        def invoke() -> tuple[RAGChunk, ...]:
            return tuple(plugin.rerank(question, list(chunks), top_n=top_n))

        return await self._runtime.blocking_runner.run(invoke)


async def build_rag_coordinator(
    config: RAGConfig,
    *,
    runtime: DocpipeRuntime,
    scope: PluginScopeHandle,
    embeddings: object,
    llm: object,
) -> tuple[RAGCoordinator, LangChainAnswerGenerator]:
    """Select a plugin and assemble one vendor-neutral RAG operation."""
    if not runtime.is_active:
        raise RuntimeError("RAG requires an active Docpipe runtime")
    if config.strategy not in _KNOWN_STRATEGIES:
        raise RAGError(
            f"Unknown strategy '{config.strategy}'. Available: {', '.join(_KNOWN_STRATEGIES)}"
        )
    _require_selected_options(config)
    provider = (
        config.vector_store.provider if config.vector_store else config.vector_backend or "pgvector"
    )
    loaded = runtime.load_plugin(PluginCategory.VECTORSTORE, provider)
    instance = await scope.acquire(
        f"rag.vectorstore.{provider}",
        lambda: loaded.create(
            _vector_plugin_config(config, provider), context=runtime.factory_context()
        ),
    )
    if not isinstance(instance, VectorStorePlugin):
        raise ConfigurationError("selected vector plugin returned an invalid binding")
    binding = instance.binding
    if VectorCapability.DENSE_SEARCH not in binding.capabilities or binding.reader is None:
        raise ConfigurationError("selected vector plugin lacks dense retrieval capability")
    encoder = LangChainEmbeddingAdapter(
        cast(LangChainEmbeddingsLike, embeddings), runtime.blocking_runner
    )
    search = VectorSearch(
        reader=binding.reader,
        encoder=encoder,
        collection=CollectionRef(config.table_name),
        capabilities=binding.capabilities,
        limit=config.top_k,
        default_filter=_typed_filters(config.filters),
    )
    generator = LangChainAnswerGenerator(config, llm, runtime.blocking_runner)
    strategies = _strategies(config, search, ModelTextRewriter(llm, runtime), runtime)
    reranker = (
        LegacyRerankerAdapter(runtime, config.reranker, config.reranker_model)
        if config.reranker != "none"
        else None
    )
    coordinator = RAGCoordinator(
        options=RAGOptions(
            strategy=config.strategy,
            top_k=config.top_k,
            max_chunks_per_source=config.max_chunks_per_source,
            rerank_top_n=config.rerank_top_n,
        ),
        strategies=strategies,
        generator=generator,
        reranker=reranker,
    )
    return coordinator, generator


_KNOWN_STRATEGIES = (
    "naive",
    "hyde",
    "multi_query",
    "parent_document",
    "hybrid",
    "auto",
    "lightrag",
)


def _require_selected_options(config: RAGConfig) -> None:
    required_prompts = {
        "hyde": ("hyde_prompt", config.hyde_prompt),
        "multi_query": ("multi_query_prompt", config.multi_query_prompt),
        "auto": ("auto_strategy_prompt", config.auto_strategy_prompt),
    }
    prompt = required_prompts.get(config.strategy)
    if prompt is not None and (prompt[1] is None or not prompt[1].strip()):
        raise ConfigurationError(f"{prompt[0]} is required for strategy '{config.strategy}'")
    if config.strategy == "lightrag" and not config.lightrag_working_dir:
        raise ConfigurationError("lightrag_working_dir is required for lightrag strategy")


def _strategies(
    config: RAGConfig,
    search: VectorSearch,
    rewriter: TextRewriter,
    runtime: DocpipeRuntime,
) -> StrategyRegistry:
    naive = NaiveStrategy(search)
    strategies: list[RetrievalStrategy] = [
        naive,
        ParentDocumentStrategy(search, config.parent_window_size),
        HybridStrategy(search),
    ]
    if config.hyde_prompt:
        strategies.append(HydeStrategy(search, rewriter, config.hyde_prompt))
    if config.multi_query_prompt:
        strategies.append(
            MultiQueryStrategy(
                search, rewriter, config.multi_query_prompt, config.multi_query_count
            )
        )
    strategies.append(
        LightRAGStrategy(
            search,
            config.lightrag_working_dir,
            graph_query_adapter(runtime.blocking_runner),
        )
    )
    available = StrategyRegistry(strategies)
    if config.auto_strategy_prompt:
        strategies.append(AutomaticStrategy(available, rewriter, config.auto_strategy_prompt))
    return StrategyRegistry(strategies)


def _typed_filters(values: dict[str, Any]) -> FilterExpression | None:
    if not values:
        return None
    filters = tuple(Equals(key, value) for key, value in values.items())
    return filters[0] if len(filters) == 1 else And(filters)


def _vector_plugin_config(config: RAGConfig, provider: str) -> PluginConfig:
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
