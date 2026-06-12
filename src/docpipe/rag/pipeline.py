"""RAGPipeline: retrieve + generate against the user's vector DB."""

from __future__ import annotations

import importlib
import math
import time
from collections.abc import Iterator
from typing import Any

from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk, RAGConfig, RAGResult, TokenUsage
from docpipe.observability.spans import set_gen_ai_usage, trace_operation
from docpipe.observability.tokens import (
    UsageCallbackHandler,
    extract_usage_from_langchain_response,
    merge_usage,
)
from docpipe.vectorstores.base import resolve_vector_backend
from docpipe.vectorstores.factory import create_vectorstore, resolve_index_dir

# Tuple: (module, class, param_map, api_key_kwarg | None)
EMBEDDING_PROVIDERS: dict[str, tuple[str, str, dict[str, str], str | None]] = {
    "openai": ("langchain_openai", "OpenAIEmbeddings", {"model": "model"}, "openai_api_key"),
    "google": (
        "langchain_google_genai",
        "GoogleGenerativeAIEmbeddings",
        {"model": "model"},
        "google_api_key",
    ),
    "ollama": ("langchain_ollama", "OllamaEmbeddings", {"model": "model"}, None),
    "huggingface": (
        "langchain_huggingface",
        "HuggingFaceEmbeddings",
        {"model_name": "model"},
        None,
    ),
}

LLM_PROVIDERS: dict[str, tuple[str, str]] = {
    "openai": ("langchain_openai", "ChatOpenAI"),
    "google": ("langchain_google_genai", "ChatGoogleGenerativeAI"),
    "ollama": ("langchain_ollama", "ChatOllama"),
    "anthropic": ("langchain_anthropic", "ChatAnthropic"),
}

# Maps provider name → kwarg name for the API key, or None if no key needed
LLM_API_KEY_PARAMS: dict[str, str | None] = {
    "openai": "api_key",
    "anthropic": "api_key",
    "google": "google_api_key",
    "ollama": None,
}


def create_llm(llm_provider: str, llm_model: str, api_key: str | None = None) -> Any:
    """Instantiate an LLM from provider name + model, optionally with a per-request api_key."""
    if llm_provider not in LLM_PROVIDERS:
        raise ConfigurationError(
            f"Unknown LLM provider: '{llm_provider}'. Available: {list(LLM_PROVIDERS)}"
        )
    module_name, class_name = LLM_PROVIDERS[llm_provider]
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
    except ImportError as err:
        raise ConfigurationError(
            f"LLM provider '{llm_provider}' requires '{module_name}'. "
            f"Install with: pip install {module_name}"
        ) from err
    kwargs: dict[str, Any] = {"model": llm_model}
    if api_key is not None:
        param = LLM_API_KEY_PARAMS.get(llm_provider)
        if param:
            kwargs[param] = api_key
    return cls(**kwargs)


def _stream_chunk_to_text(content: Any) -> str:
    """Normalize LangChain stream chunks (Gemini returns list blocks, not str)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


class RAGPipeline:
    """Retrieve relevant chunks from a vector DB and generate grounded answers."""

    STRATEGIES = [
        "naive",
        "hyde",
        "multi_query",
        "parent_document",
        "hybrid",
        "auto",
        "lightrag",
    ]

    def __init__(self, config: RAGConfig) -> None:
        self._config = config
        self._embeddings = self._create_embeddings(config)
        self._llm = self._create_llm(config)
        self._cache: list[tuple[list[float], RAGResult]] = []
        self._usage_handler = UsageCallbackHandler()
        self.last_usage: TokenUsage | None = None

    # ── Public API ───────────────────────────────────────────────────────────

    def query(self, question: str) -> RAGResult:
        """Run a RAG query against the user's vector DB."""
        if self._config.stream:
            raise ValueError(
                "RAGConfig(stream=True) requires stream_query() instead of query(). "
                "Use: pipeline.stream_query(question)"
            )
        start = time.perf_counter()
        self._usage_handler.reset()
        self.last_usage = None

        # Semantic cache lookup
        if self._config.cache_enabled:
            cached = self._cache_lookup(question)
            if cached is not None:
                return cached

        dispatch = {
            "naive": self._naive_query,
            "hyde": self._hyde_query,
            "multi_query": self._multi_query_query,
            "parent_document": self._parent_document_query,
            "hybrid": self._hybrid_query,
            "auto": self._auto_query,
            "lightrag": self._lightrag_query,
        }
        strategy = self._config.strategy
        if strategy not in dispatch:
            raise RAGError(f"Unknown strategy '{strategy}'. Available: {self.STRATEGIES}")
        with trace_operation(
            "docpipe.rag.query",
            gen_ai_operation="chat",
            provider=self._config.llm_provider,
            model=self._config.llm_model,
            docpipe_strategy=strategy,
            docpipe_table_name=self._config.table_name,
        ) as span:
            result = dispatch[strategy](question)
            result.usage = merge_usage(result.usage, self._usage_handler.usage)
            self.last_usage = result.usage
            if span is not None and result.usage is not None:
                set_gen_ai_usage(span, result.usage.model_dump())
        result.timing_seconds = time.perf_counter() - start

        if self._config.cache_enabled:
            self._cache_store(question, result)

        return result

    def stream_query(self, question: str) -> Iterator[str]:
        """Retrieve chunks (blocking), then stream answer tokens."""
        self._usage_handler.reset()
        self.last_usage = None
        dispatch = {
            "naive": self._retrieve_naive,
            "hyde": self._retrieve_hyde,
            "multi_query": self._retrieve_multi_query,
            "parent_document": self._retrieve_parent_document,
            "hybrid": self._retrieve_hybrid,
            "auto": self._retrieve_auto,
            "lightrag": self._retrieve_lightrag,
        }
        strategy = self._config.strategy
        if strategy not in dispatch:
            raise RAGError(f"Unknown strategy '{strategy}'. Available: {self.STRATEGIES}")
        with trace_operation(
            "docpipe.rag.stream",
            gen_ai_operation="chat",
            provider=self._config.llm_provider,
            model=self._config.llm_model,
            docpipe_strategy=strategy,
            docpipe_table_name=self._config.table_name,
        ):
            chunks = dispatch[strategy](question)
            context = self._build_context(chunks)
            yield from self._generate_stream(question, context)
        self.last_usage = self._usage_handler.usage

    async def aquery(self, question: str) -> RAGResult:
        """Async variant — runs query() in a thread."""
        import asyncio

        return await asyncio.to_thread(self.query, question)

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _get_vectorstore(self) -> Any:
        from docpipe.config import get_settings

        settings = get_settings()
        return create_vectorstore(
            embeddings=self._embeddings,
            table_name=self._config.table_name,
            connection_string=self._config.connection_string,
            vector_backend=resolve_vector_backend(
                config=self._config.vector_backend,
                default=settings.vector_backend,
            ),
            turbovec_index_dir=str(
                resolve_index_dir(
                    config=self._config.turbovec_index_dir,
                    default=settings.turbovec_index_dir,
                )
            ),
            turbovec_bit_width=settings.turbovec_bit_width,
        )

    def _docs_to_chunks(self, docs_with_scores: list[tuple[Any, float]]) -> list[RAGChunk]:
        return [
            RAGChunk(
                content=doc.page_content,
                score=float(score),
                source=doc.metadata.get("source", "unknown"),
                page=doc.metadata.get("page"),
                metadata=doc.metadata,
            )
            for doc, score in docs_with_scores
        ]

    @staticmethod
    def _require_prompt(name: str, value: str | None, **format_kwargs: object) -> str:
        if value is None or not str(value).strip():
            raise ConfigurationError(
                f"{name} is required. The calling application must set RAGConfig.{name} "
                f"(or pass {name} on POST /rag/query)."
            )
        if format_kwargs:
            return str(value).format(**format_kwargs)
        return str(value)

    def _build_context(self, chunks: list[RAGChunk]) -> str:
        parts = []
        for i, chunk in enumerate(chunks, 1):
            citation = chunk.source
            if chunk.page is not None:
                citation += f", page {chunk.page}"
            parts.append(f"[{i}] (Source: {citation})\n{chunk.content}")
        return "\n\n---\n\n".join(parts)

    def _llm_callbacks(self) -> list[Any]:
        return [self._usage_handler]

    def _generate(self, question: str, context: str) -> tuple[str, Any, TokenUsage | None]:
        """Generate an answer. Returns (text, structured_or_None, usage)."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        system_text = self._require_prompt(
            "system_prompt",
            self._config.system_prompt,
            context=context,
            question=question,
        )
        messages: list[Any] = [SystemMessage(content=system_text)]
        for turn in self._config.history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=question))

        invoke_config = {"callbacks": self._llm_callbacks()}

        if self._config.output_model is not None:
            structured_llm = self._llm.with_structured_output(self._config.output_model)
            result = structured_llm.invoke(messages, config=invoke_config)
            usage = self._usage_handler.usage
            return result.model_dump_json(), result, usage

        if self._config.response_format is not None:
            structured_llm = self._llm.with_structured_output(self._config.response_format)
            result = structured_llm.invoke(messages, config=invoke_config)
            usage = self._usage_handler.usage
            text = result.model_dump_json() if hasattr(result, "model_dump_json") else str(result)
            return text, result, usage

        response = self._llm.invoke(messages, config=invoke_config)
        usage = merge_usage(
            self._usage_handler.usage,
            extract_usage_from_langchain_response(response),
        )
        return _stream_chunk_to_text(response.content), None, usage

    def _generate_stream(self, question: str, context: str) -> Iterator[str]:
        """Stream answer tokens from the LLM."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        system_text = self._require_prompt(
            "system_prompt",
            self._config.system_prompt,
            context=context,
            question=question,
        )
        messages: list[Any] = [SystemMessage(content=system_text)]
        for turn in self._config.history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=question))

        last_chunk: Any = None
        for chunk in self._llm.stream(messages, config={"callbacks": self._llm_callbacks()}):
            last_chunk = chunk
            text = _stream_chunk_to_text(chunk.content)
            if text:
                yield text
        if last_chunk is not None:
            self.last_usage = merge_usage(
                self._usage_handler.usage,
                extract_usage_from_langchain_response(last_chunk),
            )

    def _cap_chunks_per_source(self, chunks: list[RAGChunk]) -> list[RAGChunk]:
        """Limit chunks per source so multi-document libraries retain coverage."""
        cap = self._config.max_chunks_per_source
        if cap <= 0 or len(chunks) <= cap:
            return chunks
        per_source: dict[str, list[RAGChunk]] = {}
        for chunk in chunks:
            per_source.setdefault(chunk.source, []).append(chunk)
        capped: list[RAGChunk] = []
        for source_chunks in per_source.values():
            source_chunks.sort(key=lambda c: c.score, reverse=True)
            capped.extend(source_chunks[:cap])
        capped.sort(key=lambda c: c.score, reverse=True)
        return capped[: self._config.top_k]

    def _finalize_retrieval(self, chunks: list[RAGChunk], question: str) -> list[RAGChunk]:
        return self._cap_chunks_per_source(self._rerank(chunks, question))

    def _rerank(self, chunks: list[RAGChunk], question: str) -> list[RAGChunk]:
        """Optional cross-encoder reranking after retrieval."""
        reranker = self._config.reranker
        if reranker == "none":
            return chunks
        top_n = self._config.rerank_top_n or self._config.top_k
        from docpipe.registry.registry import PluginRegistry

        registry = PluginRegistry.get()
        try:
            plugin = registry.get_reranker(
                reranker,
                model=self._config.reranker_model,
            )
        except Exception as e:
            raise RAGError(
                f"Reranker '{reranker}' unavailable: {e}. Available: {registry.list_rerankers()}"
            ) from e
        return plugin.rerank(question, chunks, top_n=top_n)

    def _make_result(
        self,
        question: str,
        answer: str,
        chunks: list[RAGChunk],
        structured: Any = None,
        usage: TokenUsage | None = None,
    ) -> RAGResult:
        sources = list(dict.fromkeys(c.source for c in chunks))
        result = RAGResult(
            query=question,
            answer=answer,
            strategy=self._config.strategy,
            chunks=chunks,
            sources=sources,
            timing_seconds=0.0,
            usage=usage,
        )
        result.structured = structured
        return result

    # ── Cache helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _cache_lookup(self, question: str) -> RAGResult | None:
        embedding = self._embeddings.embed_query(question)
        for cached_emb, cached_result in self._cache:
            if self._cosine_sim(embedding, cached_emb) >= self._config.cache_similarity_threshold:
                return cached_result
        return None

    def _cache_store(self, question: str, result: RAGResult) -> None:
        embedding = self._embeddings.embed_query(question)
        self._cache.append((embedding, result))
        if len(self._cache) > self._config.cache_max_size:
            self._cache.pop(0)

    # ── Retrieval-only helpers (for stream_query) ────────────────────────────

    def _retrieve_naive(self, question: str) -> list[RAGChunk]:
        vs = self._get_vectorstore()
        docs_scores = vs.similarity_search_with_score(
            question, k=self._config.top_k, filter=self._config.filters or None
        )
        return self._finalize_retrieval(self._docs_to_chunks(docs_scores), question)

    def _retrieve_hyde(self, question: str) -> list[RAGChunk]:
        from langchain_core.messages import HumanMessage

        hyde_prompt = self._require_prompt(
            "hyde_prompt",
            self._config.hyde_prompt,
            question=question,
        )
        hypothetical_doc = self._llm.invoke([HumanMessage(content=hyde_prompt)]).content
        vs = self._get_vectorstore()
        docs_scores = vs.similarity_search_with_score(
            hypothetical_doc, k=self._config.top_k, filter=self._config.filters or None
        )
        return self._finalize_retrieval(self._docs_to_chunks(docs_scores), question)

    def _retrieve_multi_query(self, question: str) -> list[RAGChunk]:
        from langchain_core.messages import HumanMessage

        prompt = self._require_prompt(
            "multi_query_prompt",
            self._config.multi_query_prompt,
            n=self._config.multi_query_count,
            question=question,
        )
        variants_text = self._llm.invoke([HumanMessage(content=prompt)]).content
        variants = [q.strip() for q in variants_text.strip().splitlines() if q.strip()]
        all_queries = [question] + variants[: self._config.multi_query_count]

        vs = self._get_vectorstore()
        seen: set[str] = set()
        merged: list[tuple[Any, float]] = []
        for q in all_queries:
            for doc, score in vs.similarity_search_with_score(
                q, k=self._config.top_k, filter=self._config.filters or None
            ):
                key = doc.page_content[:200]
                if key not in seen:
                    seen.add(key)
                    merged.append((doc, score))
        merged.sort(key=lambda x: x[1], reverse=True)
        return self._finalize_retrieval(
            self._docs_to_chunks(merged[: self._config.top_k]),
            question,
        )

    def _retrieve_parent_document(self, question: str) -> list[RAGChunk]:
        vs = self._get_vectorstore()
        seed_docs_scores = vs.similarity_search_with_score(
            question, k=self._config.top_k, filter=self._config.filters or None
        )
        seed_chunks = self._docs_to_chunks(seed_docs_scores)

        seen: set[str] = set()
        expanded: list[RAGChunk] = []
        for chunk in seed_chunks:
            key = chunk.content[:200]
            if key not in seen:
                seen.add(key)
                expanded.append(chunk)

        unique_sources = list(dict.fromkeys(c.source for c in seed_chunks))
        for source in unique_sources:
            try:
                extra = vs.similarity_search_with_score(
                    question,
                    k=self._config.parent_window_size,
                    filter={"source": source},
                )
                for doc, score in extra:
                    key = doc.page_content[:200]
                    if key not in seen:
                        seen.add(key)
                        expanded.append(
                            RAGChunk(
                                content=doc.page_content,
                                score=float(score),
                                source=doc.metadata.get("source", source),
                                page=doc.metadata.get("page"),
                                metadata=doc.metadata,
                            )
                        )
            except Exception:  # noqa: BLE001
                pass
        return self._finalize_retrieval(expanded, question)

    def _retrieve_hybrid(self, question: str) -> list[RAGChunk]:
        try:
            from langchain_community.retrievers import BM25Retriever
        except ImportError as err:
            raise RAGError(
                "Hybrid strategy requires langchain-community. "
                "Install with: pip install 'docpipe-sdk[rag]'"
            ) from err
        try:
            from langchain_classic.retrievers import EnsembleRetriever
        except ImportError as err:
            raise RAGError(
                "Hybrid strategy requires langchain-classic. "
                "Install with: pip install 'docpipe-sdk[rag]'"
            ) from err

        vs = self._get_vectorstore()
        candidate_pool_size = self._config.top_k * 10
        all_docs_scores = vs.similarity_search_with_score(
            question, k=candidate_pool_size, filter=self._config.filters or None
        )
        all_docs = [doc for doc, _ in all_docs_scores]

        bm25 = BM25Retriever.from_documents(all_docs)
        bm25.k = self._config.top_k
        filter_arg = self._config.filters or None
        search_kwargs: dict[str, Any] = {"k": self._config.top_k}
        if filter_arg:
            search_kwargs["filter"] = filter_arg
        vector_retriever = vs.as_retriever(search_kwargs=search_kwargs)
        w = self._config.hybrid_bm25_weight
        ensemble = EnsembleRetriever(retrievers=[bm25, vector_retriever], weights=[w, 1.0 - w])

        docs = ensemble.invoke(question)
        chunks_raw = [
            RAGChunk(
                content=doc.page_content,
                score=1.0,
                source=doc.metadata.get("source", "unknown"),
                page=doc.metadata.get("page"),
                metadata=doc.metadata,
            )
            for doc in docs[: self._config.top_k]
        ]
        return self._finalize_retrieval(chunks_raw, question)

    def _retrieve_auto(self, question: str) -> list[RAGChunk]:
        from langchain_core.messages import HumanMessage

        prompt = self._require_prompt(
            "auto_strategy_prompt",
            self._config.auto_strategy_prompt,
            question=question,
        )
        chosen = self._llm.invoke([HumanMessage(content=prompt)]).content.strip().lower()
        valid = ["naive", "hyde", "multi_query", "parent_document", "hybrid"]
        if chosen not in valid:
            chosen = "naive"
        retrieve_dispatch = {
            "naive": self._retrieve_naive,
            "hyde": self._retrieve_hyde,
            "multi_query": self._retrieve_multi_query,
            "parent_document": self._retrieve_parent_document,
            "hybrid": self._retrieve_hybrid,
        }
        return retrieve_dispatch[chosen](question)

    # ── Strategies ───────────────────────────────────────────────────────────

    def _naive_query(self, question: str) -> RAGResult:
        chunks = self._retrieve_naive(question)
        answer, structured, usage = self._generate(question, self._build_context(chunks))
        return self._make_result(question, answer, chunks, structured, usage)

    def _hyde_query(self, question: str) -> RAGResult:
        from langchain_core.messages import HumanMessage

        hyde_prompt = self._require_prompt(
            "hyde_prompt",
            self._config.hyde_prompt,
            question=question,
        )
        hypothetical_doc = self._llm.invoke([HumanMessage(content=hyde_prompt)]).content

        vs = self._get_vectorstore()
        docs_scores = vs.similarity_search_with_score(
            hypothetical_doc, k=self._config.top_k, filter=self._config.filters or None
        )
        chunks = self._rerank(self._docs_to_chunks(docs_scores), question)
        answer, structured, usage = self._generate(question, self._build_context(chunks))
        result = self._make_result(question, answer, chunks, structured, usage)
        result.metadata["hypothetical_doc"] = hypothetical_doc
        return result

    def _multi_query_query(self, question: str) -> RAGResult:
        from langchain_core.messages import HumanMessage

        prompt = self._require_prompt(
            "multi_query_prompt",
            self._config.multi_query_prompt,
            n=self._config.multi_query_count,
            question=question,
        )
        variants_text = self._llm.invoke([HumanMessage(content=prompt)]).content
        variants = [q.strip() for q in variants_text.strip().splitlines() if q.strip()]
        all_queries = [question] + variants[: self._config.multi_query_count]

        vs = self._get_vectorstore()
        seen: set[str] = set()
        merged: list[tuple[Any, float]] = []
        for q in all_queries:
            for doc, score in vs.similarity_search_with_score(
                q, k=self._config.top_k, filter=self._config.filters or None
            ):
                key = doc.page_content[:200]
                if key not in seen:
                    seen.add(key)
                    merged.append((doc, score))

        merged.sort(key=lambda x: x[1], reverse=True)
        chunks = self._rerank(self._docs_to_chunks(merged[: self._config.top_k]), question)
        answer, structured, usage = self._generate(question, self._build_context(chunks))
        result = self._make_result(question, answer, chunks, structured, usage)
        result.metadata["query_variants"] = variants
        return result

    def _parent_document_query(self, question: str) -> RAGResult:
        chunks = self._retrieve_parent_document(question)
        answer, structured, usage = self._generate(question, self._build_context(chunks))
        return self._make_result(question, answer, chunks, structured, usage)

    def _hybrid_query(self, question: str) -> RAGResult:
        chunks = self._retrieve_hybrid(question)
        answer, structured, usage = self._generate(question, self._build_context(chunks))
        return self._make_result(question, answer, chunks, structured, usage)

    def _retrieve_lightrag(self, question: str) -> list[RAGChunk]:
        """Retrieve via LightRAG graph index when configured."""
        try:
            from lightrag import LightRAG, QueryParam
        except ImportError as err:
            raise RAGError(
                "lightrag strategy requires the lightrag package. "
                "Install with: pip install 'docpipe-sdk[lightrag]'"
            ) from err
        if not self._config.lightrag_working_dir:
            raise ConfigurationError(
                "lightrag_working_dir is required when strategy='lightrag'. "
                "Set RAGConfig.lightrag_working_dir to an existing LightRAG working directory."
            )
        rag = LightRAG(working_dir=self._config.lightrag_working_dir)
        answer = rag.query(question, param=QueryParam(mode="hybrid"))
        if answer:
            return [
                RAGChunk(
                    content=str(answer)[:2000],
                    score=1.0,
                    source="lightrag",
                    metadata={"strategy": "lightrag"},
                )
            ]
        return self._retrieve_naive(question)

    def _lightrag_query(self, question: str) -> RAGResult:
        chunks = self._retrieve_lightrag(question)
        answer, structured, usage = self._generate(question, self._build_context(chunks))
        result = self._make_result(question, answer, chunks, structured, usage)
        result.metadata["lightrag_working_dir"] = self._config.lightrag_working_dir
        return result

    def _auto_query(self, question: str) -> RAGResult:
        from langchain_core.messages import HumanMessage

        prompt = self._require_prompt(
            "auto_strategy_prompt",
            self._config.auto_strategy_prompt,
            question=question,
        )
        chosen = self._llm.invoke([HumanMessage(content=prompt)]).content.strip().lower()
        valid = ["naive", "hyde", "multi_query", "parent_document", "hybrid"]
        if chosen not in valid:
            chosen = "naive"
        dispatch = {
            "naive": self._naive_query,
            "hyde": self._hyde_query,
            "multi_query": self._multi_query_query,
            "parent_document": self._parent_document_query,
            "hybrid": self._hybrid_query,
        }
        result = dispatch[chosen](question)
        result.metadata["auto_selected_strategy"] = chosen
        return result

    # ── Factories ────────────────────────────────────────────────────────────

    @staticmethod
    def _create_embeddings(config: RAGConfig) -> Any:
        if config.embedding_provider not in EMBEDDING_PROVIDERS:
            raise ConfigurationError(
                f"Unknown embedding provider: '{config.embedding_provider}'. "
                f"Available: {list(EMBEDDING_PROVIDERS)}"
            )
        provider_entry = EMBEDDING_PROVIDERS[config.embedding_provider]
        module_name, class_name, param_map, api_key_kwarg = provider_entry
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except ImportError as err:
            raise ConfigurationError(
                f"Embedding provider '{config.embedding_provider}' requires '{module_name}'. "
                f"Install with: pip install {module_name}"
            ) from err
        kwargs: dict[str, Any] = {param_key: config.embedding_model for param_key in param_map}
        if api_key_kwarg and config.embedding_api_key:
            kwargs[api_key_kwarg] = config.embedding_api_key
        return cls(**kwargs)

    @staticmethod
    def _create_llm(config: RAGConfig) -> Any:
        return create_llm(config.llm_provider, config.llm_model, config.llm_api_key)
