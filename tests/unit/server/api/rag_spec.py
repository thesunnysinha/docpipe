"""RAG query endpoint forwards model inputs and usage metadata."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from docpipe.core.types import RAGResult, TokenUsage


def _query_payload() -> dict[str, str]:
    """Return a fresh legacy-compatible RAG request."""
    return {
        "question": "What is X?",
        "connection_string": "postgresql://test/db",
        "table_name": "docs",
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "system_prompt": "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
        "hyde_prompt": "Hypothetical passage for: {question}",
        "multi_query_prompt": "Generate {n} variants of: {question}",
        "auto_strategy_prompt": "Reply naive for: {question}",
    }


def should_forward_request_api_key_to_llm(client) -> None:
    payload = {**_query_payload(), "api_key": "sk-test-key"}
    with patch("docpipe.rag.pipeline.create_llm") as create_llm:
        model = MagicMock()
        model.invoke.return_value = MagicMock(content="answer")
        create_llm.return_value = model
        with (
            patch("docpipe.rag.pipeline.RAGPipeline._create_embeddings") as embeddings,
            patch("docpipe.rag.pipeline.RAGPipeline.aquery", new_callable=AsyncMock) as query,
        ):
            embeddings.return_value = MagicMock()
            query.return_value = RAGResult(
                query="What is X?",
                answer="answer",
                strategy="naive",
                chunks=[],
                sources=[],
                timing_seconds=0.1,
            )
            client.post("/rag/query", json=payload)
        create_llm.assert_called_with("openai", "gpt-4o-mini", "sk-test-key")


def should_include_token_usage_when_present(client) -> None:
    with (
        patch("docpipe.rag.pipeline.RAGPipeline._create_embeddings", return_value=MagicMock()),
        patch("docpipe.rag.pipeline.create_llm", return_value=MagicMock()),
        patch("docpipe.rag.pipeline.RAGPipeline.aquery", new_callable=AsyncMock) as query,
    ):
        query.return_value = RAGResult(
            query="What is X?",
            answer="answer",
            strategy="naive",
            chunks=[],
            sources=[],
            timing_seconds=0.1,
            usage=TokenUsage(input_tokens=11, output_tokens=4, total_tokens=15),
        )
        response = client.post("/rag/query", json=_query_payload())
    assert response.status_code == 200
    assert response.json()["usage"]["input_tokens"] == 11
