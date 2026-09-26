"""Tests for secret-free, configuration-aware semantic cache namespaces."""

from docpipe.core.types import RAGConfig
from docpipe.rag.cache import cache_namespace


def _config(**overrides: object) -> RAGConfig:
    values: dict[str, object] = {
        "connection_string": "postgresql://admin:database-secret@db/docpipe",
        "table_name": "documents",
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "embedding_api_key": "embedding-secret",
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "llm_api_key": "llm-secret",
        "system_prompt": "Use {context} for {question}",
    }
    values.update(overrides)
    return RAGConfig.model_validate(values)


def test_namespace_includes_behavior_but_excludes_credentials() -> None:
    first = cache_namespace(_config())
    changed_secret = cache_namespace(
        _config(
            connection_string="postgresql://other:changed@db/docpipe",
            embedding_api_key="changed",
            llm_api_key="changed",
        )
    )
    changed_limit = cache_namespace(_config(top_k=12))

    assert first == changed_secret
    assert first != changed_limit
    assert "secret" not in first
    assert "postgresql" not in first


def test_namespace_changes_with_history_and_structured_schema() -> None:
    class Invoice:
        pass

    initial = cache_namespace(_config())
    with_history = cache_namespace(_config(history=[{"role": "user", "content": "private turn"}]))
    with_schema = cache_namespace(_config(output_model=Invoice))
    assert len({initial, with_history, with_schema}) == 3
    assert "private turn" not in with_history
