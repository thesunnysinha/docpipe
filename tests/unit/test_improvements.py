"""Unit tests for v0.3.0 improvements: contextual injection, semantic cache,
chunk methods, streaming RAG, and agentic RAG (strategy=auto)."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from docpipe.core.types import IngestionConfig, RAGConfig, RAGResult
from docpipe.ingestion.pipeline import IngestionPipeline
from docpipe.rag.pipeline import RAGPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rag_config(**overrides: object) -> RAGConfig:
    defaults = dict(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        llm_provider="openai",
        llm_model="gpt-4o",
    )
    defaults.update(overrides)
    return RAGConfig(**defaults)  # type: ignore[arg-type]


def _make_ingest_config(**overrides: object) -> IngestionConfig:
    defaults = dict(
        connection_string="postgresql://test/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )
    defaults.update(overrides)
    return IngestionConfig(**defaults)  # type: ignore[arg-type]


def _make_rag_result(question: str = "What is X?", answer: str = "X is Y.") -> RAGResult:
    from docpipe.core.types import RAGChunk

    return RAGResult(
        query=question,
        answer=answer,
        strategy="naive",
        chunks=[RAGChunk(content="chunk text", score=0.9, source="doc.pdf")],
        sources=["doc.pdf"],
        timing_seconds=0.1,
    )


# ---------------------------------------------------------------------------
# Feature 1: Contextual Chunk Injection
# ---------------------------------------------------------------------------


class TestContextualInjection:
    @patch.object(IngestionPipeline, "_create_embeddings")
    def test_injection_disabled_by_default(self, mock_emb: MagicMock) -> None:
        mock_emb.return_value = MagicMock()
        config = _make_ingest_config()
        assert config.contextual_injection is False

    @patch.object(IngestionPipeline, "_create_embeddings")
    @patch.object(IngestionPipeline, "_create_context_llm")
    @patch.object(IngestionPipeline, "_inject_context")
    def test_injection_called_when_enabled(
        self,
        mock_inject: MagicMock,
        mock_llm: MagicMock,
        mock_emb: MagicMock,
    ) -> None:
        """When contextual_injection=True, _inject_context must be called."""
        import sys
        mock_emb.return_value = MagicMock()
        mock_llm.return_value = MagicMock()
        mock_inject.side_effect = lambda chunks, full_text, llm: chunks

        config = _make_ingest_config(contextual_injection=True)
        pipeline = IngestionPipeline(config)

        from docpipe.core.types import DocumentFormat, ParsedDocument

        parsed = ParsedDocument(
            source="test.pdf",
            format=DocumentFormat.PDF,
            text="Full document text here.",
            markdown="",
        )

        fake_pgvector = MagicMock()
        with patch.dict(sys.modules, {"langchain_postgres": fake_pgvector}):
            pipeline.ingest(parsed)

        mock_inject.assert_called_once()

    @patch.object(IngestionPipeline, "_create_embeddings")
    @patch.object(IngestionPipeline, "_create_context_llm")
    @patch.object(IngestionPipeline, "_inject_context")
    def test_injection_not_called_when_disabled(
        self,
        mock_inject: MagicMock,
        mock_llm: MagicMock,
        mock_emb: MagicMock,
    ) -> None:
        import sys
        mock_emb.return_value = MagicMock()
        config = _make_ingest_config(contextual_injection=False)
        pipeline = IngestionPipeline(config)

        from docpipe.core.types import DocumentFormat, ParsedDocument

        parsed = ParsedDocument(
            source="test.pdf",
            format=DocumentFormat.PDF,
            text="Full document text here.",
            markdown="",
        )

        fake_pgvector = MagicMock()
        with patch.dict(sys.modules, {"langchain_postgres": fake_pgvector}):
            pipeline.ingest(parsed)

        mock_inject.assert_not_called()

    def test_inject_context_prepends_sentence(self) -> None:
        """_inject_context prepends LLM context to each chunk's page_content."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "This chunk discusses X."

        chunk = MagicMock()
        chunk.page_content = "Original chunk content."

        IngestionPipeline._inject_context([chunk], "Full doc text.", mock_llm)

        assert chunk.page_content == "This chunk discusses X.\n\nOriginal chunk content."


# ---------------------------------------------------------------------------
# Feature 2: Semantic Query Cache
# ---------------------------------------------------------------------------


class TestSemanticQueryCache:
    def test_cache_disabled_by_default(self) -> None:
        config = _make_rag_config()
        assert config.cache_enabled is False
        assert config.cache_similarity_threshold == 0.95
        assert config.cache_max_size == 100

    def test_cosine_sim_identical_vectors(self) -> None:
        v = [1.0, 0.0, 0.0]
        assert RAGPipeline._cosine_sim(v, v) == pytest.approx(1.0)

    def test_cosine_sim_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert RAGPipeline._cosine_sim(a, b) == pytest.approx(0.0)

    def test_cosine_sim_zero_vector(self) -> None:
        assert RAGPipeline._cosine_sim([0.0, 0.0], [1.0, 0.0]) == 0.0

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_cache_hit_skips_llm(self, mock_llm: MagicMock, mock_emb: MagicMock) -> None:
        """Second identical query should return cached result without calling strategy."""
        mock_emb.return_value = MagicMock()
        mock_emb.return_value.embed_query.return_value = [1.0, 0.0, 0.0]
        mock_llm.return_value = MagicMock()

        config = _make_rag_config(cache_enabled=True, cache_similarity_threshold=0.9)
        pipeline = RAGPipeline(config)

        cached_result = _make_rag_result()
        pipeline._cache = [([1.0, 0.0, 0.0], cached_result)]

        with patch.object(pipeline, "_naive_query") as mock_naive:
            result = pipeline.query("What is X?")

        mock_naive.assert_not_called()
        assert result is cached_result

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_cache_miss_runs_retrieval(self, mock_llm: MagicMock, mock_emb: MagicMock) -> None:
        mock_emb.return_value = MagicMock()
        mock_emb.return_value.embed_query.return_value = [0.0, 1.0, 0.0]
        mock_llm.return_value = MagicMock()

        config = _make_rag_config(cache_enabled=True, cache_similarity_threshold=0.9)
        pipeline = RAGPipeline(config)

        cached_result = _make_rag_result(answer="Cached answer")
        pipeline._cache = [([1.0, 0.0, 0.0], cached_result)]

        fresh_result = _make_rag_result(answer="Fresh answer")
        with patch.object(pipeline, "_naive_query", return_value=fresh_result):
            result = pipeline.query("Different question?")

        assert result.answer == "Fresh answer"

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_cache_stores_result(self, mock_llm: MagicMock, mock_emb: MagicMock) -> None:
        mock_emb.return_value = MagicMock()
        mock_emb.return_value.embed_query.return_value = [1.0, 0.0, 0.0]
        mock_llm.return_value = MagicMock()

        config = _make_rag_config(cache_enabled=True)
        pipeline = RAGPipeline(config)

        result = _make_rag_result()
        with patch.object(pipeline, "_naive_query", return_value=result):
            pipeline.query("What is X?")

        assert len(pipeline._cache) == 1

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_cache_evicts_oldest_when_full(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        mock_emb.return_value = MagicMock()
        mock_emb.return_value.embed_query.return_value = [0.0, 0.0, 1.0]
        mock_llm.return_value = MagicMock()

        config = _make_rag_config(cache_enabled=True, cache_max_size=2)
        pipeline = RAGPipeline(config)

        r1 = _make_rag_result(answer="R1")
        r2 = _make_rag_result(answer="R2")
        pipeline._cache = [([1.0, 0.0, 0.0], r1), ([0.0, 1.0, 0.0], r2)]

        r3 = _make_rag_result(answer="R3")
        with patch.object(pipeline, "_naive_query", return_value=r3):
            pipeline.query("New question?")

        assert len(pipeline._cache) == 2
        assert pipeline._cache[0][1].answer == "R2"  # oldest evicted
        assert pipeline._cache[1][1].answer == "R3"


# ---------------------------------------------------------------------------
# Feature 3: Domain-Specific Chunk Methods
# ---------------------------------------------------------------------------


class TestChunkMethods:
    def test_default_method_uses_config_size(self) -> None:
        config = _make_ingest_config(chunk_size=500, chunk_overlap=50)
        splitter = IngestionPipeline._create_splitter(config)
        assert splitter._chunk_size == 500
        assert splitter._chunk_overlap == 50

    @pytest.mark.parametrize(
        "method,expected_size",
        [
            ("paper", 1500),
            ("laws", 2000),
            ("book", 2000),
            ("qa", 500),
            ("manual", 800),
            ("table", 500),
            ("presentation", 600),
        ],
    )
    def test_method_splitter_sizes(self, method: str, expected_size: int) -> None:
        config = _make_ingest_config(chunk_method=method)  # type: ignore[arg-type]
        splitter = IngestionPipeline._create_splitter(config)
        assert splitter._chunk_size == expected_size

    def test_paper_separators_include_heading(self) -> None:
        config = _make_ingest_config(chunk_method="paper")
        splitter = IngestionPipeline._create_splitter(config)
        assert "\n## " in splitter._separators

    def test_table_has_zero_overlap(self) -> None:
        config = _make_ingest_config(chunk_method="table")
        splitter = IngestionPipeline._create_splitter(config)
        assert splitter._chunk_overlap == 0

    def test_presentation_splits_on_slide_divider(self) -> None:
        config = _make_ingest_config(chunk_method="presentation")
        splitter = IngestionPipeline._create_splitter(config)
        assert "\n---" in splitter._separators


# ---------------------------------------------------------------------------
# Feature 4: Streaming RAG
# ---------------------------------------------------------------------------


class TestStreamingRAG:
    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_query_raises_when_stream_true(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        mock_emb.return_value = MagicMock()
        mock_llm.return_value = MagicMock()

        config = _make_rag_config(stream=True)
        pipeline = RAGPipeline(config)
        with pytest.raises(ValueError, match="stream_query"):
            pipeline.query("What is X?")

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_stream_query_returns_iterator(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        mock_emb.return_value = MagicMock()
        mock_llm.return_value = MagicMock()

        config = _make_rag_config(stream=True)
        pipeline = RAGPipeline(config)

        with patch.object(pipeline, "_retrieve_naive", return_value=[]):
            with patch.object(
                pipeline, "_generate_stream", return_value=iter(["Hello", " world"])
            ):
                result = pipeline.stream_query("What is X?")

        assert isinstance(result, Iterator)

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_stream_query_yields_strings(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        mock_emb.return_value = MagicMock()
        mock_llm.return_value = MagicMock()

        config = _make_rag_config()
        pipeline = RAGPipeline(config)

        tokens = ["The ", "answer ", "is ", "42."]
        with patch.object(pipeline, "_retrieve_naive", return_value=[]):
            with patch.object(pipeline, "_generate_stream", return_value=iter(tokens)):
                result = list(pipeline.stream_query("What is X?"))

        assert result == tokens

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_generate_stream_calls_llm_stream(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        """_generate_stream should call self._llm.stream() and yield chunk.content."""
        mock_emb.return_value = MagicMock()
        llm_instance = MagicMock()
        mock_llm.return_value = llm_instance

        token1 = MagicMock()
        token1.content = "Hello"
        token2 = MagicMock()
        token2.content = " world"
        llm_instance.stream.return_value = [token1, token2]

        config = _make_rag_config()
        pipeline = RAGPipeline(config)

        tokens = list(pipeline._generate_stream("What is X?", "Some context."))
        assert tokens == ["Hello", " world"]
        llm_instance.stream.assert_called_once()


# ---------------------------------------------------------------------------
# Feature 5: Agentic RAG (strategy=auto)
# ---------------------------------------------------------------------------


class TestAgenticRAG:
    def test_auto_in_strategies_list(self) -> None:
        assert "auto" in RAGPipeline.STRATEGIES

    def test_rag_config_accepts_auto_strategy(self) -> None:
        config = _make_rag_config(strategy="auto")
        assert config.strategy == "auto"

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_auto_dispatches_to_chosen_strategy(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        """When LLM returns 'hyde', _hyde_query should be called."""
        mock_emb.return_value = MagicMock()
        llm_instance = MagicMock()
        llm_instance.invoke.return_value.content = "hyde"
        mock_llm.return_value = llm_instance

        config = _make_rag_config(strategy="auto")
        pipeline = RAGPipeline(config)

        expected_result = _make_rag_result()
        with patch.object(pipeline, "_hyde_query", return_value=expected_result) as mock_hyde:
            result = pipeline.query("What is a hypothetical answer?")

        mock_hyde.assert_called_once_with("What is a hypothetical answer?")
        assert result.metadata["auto_selected_strategy"] == "hyde"

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_auto_falls_back_to_naive_on_invalid_response(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        """Invalid LLM response should fall back to 'naive'."""
        mock_emb.return_value = MagicMock()
        llm_instance = MagicMock()
        llm_instance.invoke.return_value.content = "totally_invalid_strategy"
        mock_llm.return_value = llm_instance

        config = _make_rag_config(strategy="auto")
        pipeline = RAGPipeline(config)

        expected_result = _make_rag_result()
        with patch.object(pipeline, "_naive_query", return_value=expected_result) as mock_naive:
            result = pipeline.query("Some question?")

        mock_naive.assert_called_once()
        assert result.metadata["auto_selected_strategy"] == "naive"

    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_auto_metadata_contains_strategy(
        self, mock_llm: MagicMock, mock_emb: MagicMock
    ) -> None:
        mock_emb.return_value = MagicMock()
        llm_instance = MagicMock()
        llm_instance.invoke.return_value.content = "hybrid"
        mock_llm.return_value = llm_instance

        config = _make_rag_config(strategy="auto")
        pipeline = RAGPipeline(config)

        expected_result = _make_rag_result()
        with patch.object(pipeline, "_hybrid_query", return_value=expected_result):
            result = pipeline.query("Technical keyword query?")

        assert result.metadata.get("auto_selected_strategy") == "hybrid"

    @pytest.mark.parametrize(
        "strategy", ["naive", "hyde", "multi_query", "parent_document", "hybrid"]
    )
    @patch.object(RAGPipeline, "_create_embeddings")
    @patch.object(RAGPipeline, "_create_llm")
    def test_auto_dispatches_each_valid_strategy(
        self, mock_llm: MagicMock, mock_emb: MagicMock, strategy: str
    ) -> None:
        mock_emb.return_value = MagicMock()
        llm_instance = MagicMock()
        llm_instance.invoke.return_value.content = strategy
        mock_llm.return_value = llm_instance

        config = _make_rag_config(strategy="auto")
        pipeline = RAGPipeline(config)

        expected_result = _make_rag_result()
        method_name = f"_{strategy}_query"
        with patch.object(pipeline, method_name, return_value=expected_result):
            result = pipeline.query("Some question?")

        assert result.metadata["auto_selected_strategy"] == strategy
