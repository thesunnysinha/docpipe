"""RAGPipeline: retrieve + generate against the user's vector DB."""

from __future__ import annotations

import importlib
import math
import time
from collections.abc import Iterator
from typing import Any

from docpipe.core.errors import ConfigurationError, RAGError
from docpipe.core.types import RAGChunk, RAGConfig, RAGResult

EMBEDDING_PROVIDERS: dict[str, tuple[str, str, dict[str, str]]] = {
    "openai": ("langchain_openai", "OpenAIEmbeddings", {"model": "model"}),
    "google": ("langchain_google_genai", "GoogleGenerativeAIEmbeddings", {"model": "model"}),
    "ollama": ("langchain_ollama", "OllamaEmbeddings", {"model": "model"}),
    "huggingface": ("langchain_huggingface", "HuggingFaceEmbeddings", {"model_name": "model"}),
}

LLM_PROVIDERS: dict[str, tuple[str, str]] = {
    "openai": ("langchain_openai", "ChatOpenAI"),
    "google": ("langchain_google_genai", "ChatGoogleGenerativeAI"),
    "ollama": ("langchain_ollama", "ChatOllama"),
    "anthropic": ("langchain_anthropic", "ChatAnthropic"),
}

DEFAULT_SYSTEM_PROMPT = """\
You are a helpful assistant. Answer the question using ONLY the provided context.
If the context does not contain enough information to answer, say so explicitly.
Cite the source documents by name when making claims.

Context:
{context}

Question: {question}

Answer:"""

HYDE_GENERATION_PROMPT = """\
Generate a detailed document passage that would answer the following question.
Write the passage as if it were an excerpt from an authoritative reference document.
Do not start with "Here is..." — write the passage directly.

Question: {question}"""

MULTI_QUERY_PROMPT = """\
Generate {n} different phrasings of the following question.
Each phrasing should approach the same information need from a different angle.
Output one question per line, no numbering or bullets.

Original question: {question}"""

AUTO_STRATEGY_PROMPT = """\
Given this question, which retrieval strategy is best?
- naive: simple factual lookup
- hyde: complex or abstract questions benefiting from hypothetical framing
- multi_query: ambiguous questions that benefit from multiple phrasings
- parent_document: questions needing broader surrounding context
- hybrid: keyword-heavy or technical queries

Question: {question}
Reply with exactly one word: naive, hyde, multi_query, parent_document, or hybrid."""


class RAGPipeline:
    """Retrieve relevant chunks from a vector DB and generate grounded answers."""

    STRATEGIES = ["naive", "hyde", "multi_query", "parent_document", "hybrid", "auto"]

    def __init__(self, config: RAGConfig) -> None:
        self._config = config
        self._embeddings = self._create_embeddings(config)
        self._llm = self._create_llm(config)
        self._cache: list[tuple[list[float], RAGResult]] = []

    # ── Public API ───────────────────────────────────────────────────────────

    def query(self, question: str) -> RAGResult:
        """Run a RAG query against the user's vector DB."""
        if self._config.stream:
            raise ValueError(
                "RAGConfig(stream=True) requires stream_query() instead of query(). "
                "Use: pipeline.stream_query(question)"
            )
        start = time.perf_counter()

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
        }
        strategy = self._config.strategy
        if strategy not in dispatch:
            raise RAGError(f"Unknown strategy '{strategy}'. Available: {self.STRATEGIES}")
        result = dispatch[strategy](question)
        result.timing_seconds = time.perf_counter() - start

        if self._config.cache_enabled:
            self._cache_store(question, result)

        return result

    def stream_query(self, question: str) -> Iterator[str]:
        """Retrieve chunks (blocking), then stream answer tokens."""
        dispatch = {
            "naive": self._retrieve_naive,
            "hyde": self._retrieve_hyde,
            "multi_query": self._retrieve_multi_query,
            "parent_document": self._retrieve_parent_document,
            "hybrid": self._retrieve_hybrid,
            "auto": self._retrieve_auto,
        }
        strategy = self._config.strategy
        if strategy not in dispatch:
            raise RAGError(f"Unknown strategy '{strategy}'. Available: {self.STRATEGIES}")
        chunks = dispatch[strategy](question)
        context = self._build_context(chunks)
        return self._generate_stream(question, context)

    async def aquery(self, question: str) -> RAGResult:
        """Async variant — runs query() in a thread."""
        import asyncio

        return await asyncio.to_thread(self.query, question)

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _get_vectorstore(self) -> Any:
        from langchain_postgres import PGVector

        return PGVector(
            embeddings=self._embeddings,
            collection_name=self._config.table_name,
            connection=self._config.connection_string,
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

    def _build_context(self, chunks: list[RAGChunk]) -> str:
        parts = []
        for i, chunk in enumerate(chunks, 1):
            citation = chunk.source
            if chunk.page is not None:
                citation += f", page {chunk.page}"
            parts.append(f"[{i}] (Source: {citation})\n{chunk.content}")
        return "\n\n---\n\n".join(parts)

    def _generate(self, question: str, context: str) -> tuple[str, Any]:
        """Generate an answer. Returns (text, structured_or_None)."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        system_text = (self._config.system_prompt or DEFAULT_SYSTEM_PROMPT).format(
            context=context, question=question
        )
        messages: list[Any] = [SystemMessage(content=system_text)]
        for turn in self._config.history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=question))

        if self._config.output_model is not None:
            structured_llm = self._llm.with_structured_output(self._config.output_model)
            result = structured_llm.invoke(messages)
            return result.model_dump_json(), result

        response = self._llm.invoke(messages)
        return response.content, None

    def _generate_stream(self, question: str, context: str) -> Iterator[str]:
        """Stream answer tokens from the LLM."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        system_text = (self._config.system_prompt or DEFAULT_SYSTEM_PROMPT).format(
            context=context, question=question
        )
        messages: list[Any] = [SystemMessage(content=system_text)]
        for turn in self._config.history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))
        messages.append(HumanMessage(content=question))

        for chunk in self._llm.stream(messages):
            yield chunk.content

    def _rerank(self, chunks: list[RAGChunk], question: str) -> list[RAGChunk]:
        """Optional cross-encoder reranking after retrieval."""
        reranker = self._config.reranker
        if reranker == "none":
            return chunks
        top_n = self._config.rerank_top_n or self._config.top_k
        if reranker == "flashrank":
            try:
                from flashrank import Ranker as FlashRanker
                from flashrank import RerankRequest
            except ImportError as err:
                raise RAGError(
                    "flashrank reranker requires the 'flashrank' package. "
                    "Install with: pip install 'docpipe-sdk[rerank]'"
                ) from err
            model = self._config.reranker_model or "ms-marco-MiniLM-L-12-v2"
            ranker = FlashRanker(model_name=model)
            request = RerankRequest(
                query=question, passages=[{"text": c.content} for c in chunks]
            )
            results = ranker.rerank(request)
            reranked = [chunks[r["index"]] for r in results]
            return reranked[:top_n]
        if reranker == "cohere":
            try:
                import cohere
            except ImportError as err:
                raise RAGError(
                    "cohere reranker requires the 'cohere' package. "
                    "Install with: pip install 'docpipe-sdk[rerank]'"
                ) from err
            model = self._config.reranker_model or "rerank-english-v3.0"
            co = cohere.Client()
            docs = [c.content for c in chunks]
            response = co.rerank(query=question, documents=docs, model=model, top_n=top_n)
            reranked = [chunks[r.index] for r in response.results]
            return reranked
        raise RAGError(f"Unknown reranker '{reranker}'. Available: none, flashrank, cohere")

    def _make_result(
        self, question: str, answer: str, chunks: list[RAGChunk], structured: Any = None
    ) -> RAGResult:
        sources = list(dict.fromkeys(c.source for c in chunks))
        result = RAGResult(
            query=question,
            answer=answer,
            strategy=self._config.strategy,
            chunks=chunks,
            sources=sources,
            timing_seconds=0.0,
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
        return self._rerank(self._docs_to_chunks(docs_scores), question)

    def _retrieve_hyde(self, question: str) -> list[RAGChunk]:
        from langchain_core.messages import HumanMessage

        hyde_prompt = (self._config.hyde_prompt or HYDE_GENERATION_PROMPT).format(
            question=question
        )
        hypothetical_doc = self._llm.invoke([HumanMessage(content=hyde_prompt)]).content
        vs = self._get_vectorstore()
        docs_scores = vs.similarity_search_with_score(
            hypothetical_doc, k=self._config.top_k, filter=self._config.filters or None
        )
        return self._rerank(self._docs_to_chunks(docs_scores), question)

    def _retrieve_multi_query(self, question: str) -> list[RAGChunk]:
        from langchain_core.messages import HumanMessage

        prompt = MULTI_QUERY_PROMPT.format(n=self._config.multi_query_count, question=question)
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
        return self._rerank(self._docs_to_chunks(merged[: self._config.top_k]), question)

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
        return self._rerank(expanded, question)

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
        vector_retriever = vs.as_retriever(search_kwargs={"k": self._config.top_k})
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
        return self._rerank(chunks_raw, question)

    def _retrieve_auto(self, question: str) -> list[RAGChunk]:
        from langchain_core.messages import HumanMessage

        prompt = AUTO_STRATEGY_PROMPT.format(question=question)
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
        answer, structured = self._generate(question, self._build_context(chunks))
        return self._make_result(question, answer, chunks, structured)

    def _hyde_query(self, question: str) -> RAGResult:
        from langchain_core.messages import HumanMessage

        hyde_prompt = (self._config.hyde_prompt or HYDE_GENERATION_PROMPT).format(
            question=question
        )
        hypothetical_doc = self._llm.invoke([HumanMessage(content=hyde_prompt)]).content

        vs = self._get_vectorstore()
        docs_scores = vs.similarity_search_with_score(
            hypothetical_doc, k=self._config.top_k, filter=self._config.filters or None
        )
        chunks = self._rerank(self._docs_to_chunks(docs_scores), question)
        answer, structured = self._generate(question, self._build_context(chunks))
        result = self._make_result(question, answer, chunks, structured)
        result.metadata["hypothetical_doc"] = hypothetical_doc
        return result

    def _multi_query_query(self, question: str) -> RAGResult:
        from langchain_core.messages import HumanMessage

        prompt = MULTI_QUERY_PROMPT.format(n=self._config.multi_query_count, question=question)
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
        answer, structured = self._generate(question, self._build_context(chunks))
        result = self._make_result(question, answer, chunks, structured)
        result.metadata["query_variants"] = variants
        return result

    def _parent_document_query(self, question: str) -> RAGResult:
        chunks = self._retrieve_parent_document(question)
        answer, structured = self._generate(question, self._build_context(chunks))
        return self._make_result(question, answer, chunks, structured)

    def _hybrid_query(self, question: str) -> RAGResult:
        chunks = self._retrieve_hybrid(question)
        answer, structured = self._generate(question, self._build_context(chunks))
        return self._make_result(question, answer, chunks, structured)

    def _auto_query(self, question: str) -> RAGResult:
        from langchain_core.messages import HumanMessage

        prompt = AUTO_STRATEGY_PROMPT.format(question=question)
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
        module_name, class_name, param_map = EMBEDDING_PROVIDERS[config.embedding_provider]
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except ImportError as err:
            raise ConfigurationError(
                f"Embedding provider '{config.embedding_provider}' requires '{module_name}'. "
                f"Install with: pip install {module_name}"
            ) from err
        kwargs = {param_key: config.embedding_model for param_key in param_map}
        return cls(**kwargs)

    @staticmethod
    def _create_llm(config: RAGConfig) -> Any:
        if config.llm_provider not in LLM_PROVIDERS:
            raise ConfigurationError(
                f"Unknown LLM provider: '{config.llm_provider}'. "
                f"Available: {list(LLM_PROVIDERS)}"
            )
        module_name, class_name = LLM_PROVIDERS[config.llm_provider]
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except ImportError as err:
            raise ConfigurationError(
                f"LLM provider '{config.llm_provider}' requires '{module_name}'. "
                f"Install with: pip install {module_name}"
            ) from err
        return cls(model=config.llm_model)
