"""Public SDK compatibility facade over the composed RAG coordinator."""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any, cast

from docpipe.bootstrap.runtime import DocpipeRuntime, build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import RAGChunk, RAGConfig, RAGResult, TokenUsage
from docpipe.embeddings.langchain_adapter import LangChainEmbeddingAdapter, LangChainEmbeddingsLike
from docpipe.plugins.lifecycle import PluginScopeHandle
from docpipe.rag.cache import cache_namespace
from docpipe.rag.composition import build_rag_coordinator
from docpipe.rag.generation import build_context, normalize_content
from docpipe.rag.providers import create_embeddings, create_llm

_stream_chunk_to_text = normalize_content


class RAGPipeline:
    """Preserve synchronous and async SDK calls with explicit runtime ownership.

    An injected runtime remains caller-owned and must already be active. For
    standalone SDK calls, each operation creates and closes a short-lived
    runtime, including on cancellation or early stream closure.
    """

    STRATEGIES = ["naive", "hyde", "multi_query", "parent_document", "hybrid", "auto", "lightrag"]

    def __init__(self, config: RAGConfig, *, runtime: DocpipeRuntime | None = None) -> None:
        self._config = config
        self._runtime = runtime
        self._embeddings = self._create_embeddings(config)
        self._llm = self._create_llm(config)
        self._cache: list[tuple[str, tuple[float, ...], RAGResult]] = []
        self.last_usage: TokenUsage | None = None

    def query(self, question: str) -> RAGResult:
        """Synchronously query from a thread without an active event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.aquery(question))
        raise ConfigurationError("query() cannot run inside an event loop; use aquery()")

    async def aquery(self, question: str) -> RAGResult:
        """Retrieve and generate with scope-safe, cancellation-aware ownership."""
        if self._config.stream:
            raise ValueError("RAGConfig(stream=True) requires stream_query()")
        if self._runtime is not None:
            if not self._runtime.is_active:
                raise RuntimeError("caller-owned Docpipe runtime is not active")
            return await self._query_with_runtime(question, self._runtime)
        async with _compatibility_runtime() as runtime:
            return await self._query_with_runtime(question, runtime)

    async def _query_with_runtime(self, question: str, runtime: DocpipeRuntime) -> RAGResult:
        if self._config.cache_enabled:
            cached = await self._cache_lookup(question, runtime)
            if cached is not None:
                self.last_usage = cached.usage
                return cached.model_copy(deep=True)
        async with _operation_scope(runtime) as scope:
            coordinator, _generator = await build_rag_coordinator(
                self._config,
                runtime=runtime,
                scope=scope,
                embeddings=self._embeddings,
                llm=self._llm,
            )
            result = await coordinator.query(question)
        self.last_usage = result.usage
        if self._config.cache_enabled:
            await self._cache_store(question, result, runtime)
        return result

    async def aretrieve_chunks(self, question: str) -> tuple[RAGChunk, ...]:
        """Retrieve chunks without generation for agent and evaluation callers."""
        if self._runtime is not None:
            if not self._runtime.is_active:
                raise RuntimeError("caller-owned Docpipe runtime is not active")
            return await self._retrieve_with_runtime(question, self._runtime)
        async with _compatibility_runtime() as runtime:
            return await self._retrieve_with_runtime(question, runtime)

    async def _retrieve_with_runtime(
        self, question: str, runtime: DocpipeRuntime
    ) -> tuple[RAGChunk, ...]:
        async with _operation_scope(runtime) as scope:
            coordinator, _generator = await build_rag_coordinator(
                self._config,
                runtime=runtime,
                scope=scope,
                embeddings=self._embeddings,
                llm=self._llm,
            )
            return (await coordinator.prepare(question)).chunks

    def retrieve_chunks(self, question: str) -> tuple[RAGChunk, ...]:
        """Synchronous retrieval-only API for legacy agent tools."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.aretrieve_chunks(question))
        raise ConfigurationError(
            "retrieve_chunks() cannot run inside an event loop; use aretrieve_chunks()"
        )

    async def astream_query(self, question: str) -> AsyncIterator[str]:
        """Stream model fragments while retaining runtime ownership."""
        if self._runtime is not None:
            if not self._runtime.is_active:
                raise RuntimeError("caller-owned Docpipe runtime is not active")
            async for token in self._stream_with_runtime(question, self._runtime):
                yield token
            return
        async with _compatibility_runtime() as runtime:
            async for token in self._stream_with_runtime(question, runtime):
                yield token

    async def _stream_with_runtime(
        self, question: str, runtime: DocpipeRuntime
    ) -> AsyncIterator[str]:
        async with _operation_scope(runtime) as scope:
            coordinator, generator = await build_rag_coordinator(
                self._config,
                runtime=runtime,
                scope=scope,
                embeddings=self._embeddings,
                llm=self._llm,
            )
            prepared = await coordinator.prepare(question)
            self.last_usage = None
            async for token in generator.stream(question, prepared.context):
                yield token
            self.last_usage = generator.last_usage

    def stream_query(self, question: str) -> Iterator[str]:
        """Bridge the async streaming port for existing synchronous callers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise ConfigurationError(
                "stream_query() cannot run inside an event loop; use astream_query()"
            )
        loop = asyncio.new_event_loop()
        stream = cast(AsyncGenerator[str, None], self.astream_query(question))
        try:
            while True:
                try:
                    yield loop.run_until_complete(anext(stream))
                except StopAsyncIteration:
                    return
        finally:
            loop.run_until_complete(stream.aclose())
            loop.close()

    async def _cache_vector(self, question: str, runtime: DocpipeRuntime) -> tuple[float, ...]:
        adapter = LangChainEmbeddingAdapter(
            cast(LangChainEmbeddingsLike, self._embeddings), runtime.blocking_runner
        )
        return await adapter.encode_query(question)

    async def _cache_lookup(self, question: str, runtime: DocpipeRuntime) -> RAGResult | None:
        identity = cache_namespace(self._config)
        vector = await self._cache_vector(question, runtime)
        for namespace, cached_vector, result in self._cache:
            if namespace != identity:
                continue
            if self._cosine_sim(vector, cached_vector) >= self._config.cache_similarity_threshold:
                return result
        return None

    async def _cache_store(self, question: str, result: RAGResult, runtime: DocpipeRuntime) -> None:
        vector = await self._cache_vector(question, runtime)
        self._cache.append((cache_namespace(self._config), vector, result.model_copy(deep=True)))
        if len(self._cache) > self._config.cache_max_size:
            self._cache.pop(0)

    @staticmethod
    def _cosine_sim(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        """Return cosine similarity, including a safe zero-vector fallback."""
        if len(a) != len(b):
            return 0.0
        norm_a = math.sqrt(sum(value * value for value in a))
        norm_b = math.sqrt(sum(value * value for value in b))
        if not norm_a or not norm_b:
            return 0.0
        return sum(left * right for left, right in zip(a, b, strict=True)) / (norm_a * norm_b)

    def _build_context(self, chunks: list[RAGChunk]) -> str:
        """Keep a deprecated patchable context-rendering seam."""
        return build_context(tuple(chunks))

    def result_from_chunks(
        self, question: str, answer: str, chunks: tuple[RAGChunk, ...]
    ) -> RAGResult:
        """Build a stable agent result without invoking answer generation."""
        return RAGResult(
            query=question,
            answer=answer,
            strategy=self._config.strategy,
            chunks=list(chunks),
            sources=list(dict.fromkeys(chunk.source for chunk in chunks)),
            timing_seconds=0.0,
        )

    @staticmethod
    def _create_embeddings(config: RAGConfig) -> Any:
        """Keep the SDK's patchable embedding-provider construction seam."""
        return create_embeddings(config)

    @staticmethod
    def _create_llm(config: RAGConfig) -> Any:
        """Keep the SDK's patchable model-provider construction seam."""
        return create_llm(config.llm_provider, config.llm_model, config.llm_api_key)


def _compatibility_runtime() -> DocpipeRuntime:
    """Build an explicit SDK runtime without reading process-global settings."""
    settings = DocpipeSettings.model_construct(max_concurrency=4, disabled_plugins=None)
    return build_runtime(settings)


@asynccontextmanager
async def _operation_scope(runtime: DocpipeRuntime) -> AsyncIterator[PluginScopeHandle]:
    """Release selected operation resources on success, failure, or cancellation."""
    async with (
        runtime.plugin_runtime.request_scope() as request,
        request.operation_scope() as operation,
    ):
        yield operation
