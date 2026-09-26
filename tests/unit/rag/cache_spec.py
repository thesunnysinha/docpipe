"""Tests for secret-free, configuration-aware semantic cache namespaces."""

from docpipe.core.types import RAGConfig
from docpipe.rag.cache import cache_key, cache_namespace


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


def test_namespace_includes_behavior_and_credential_fingerprints() -> None:
    first = cache_namespace(_config())
    changed_secret = cache_namespace(
        _config(
            connection_string="postgresql://other:changed@db/docpipe",
            embedding_api_key="changed",
            llm_api_key="changed",
        )
    )
    changed_limit = cache_namespace(_config(top_k=12))

    assert first != changed_secret
    assert first != changed_limit
    assert "secret" not in first
    assert "postgresql" not in first
    assert "database-secret" not in first
    assert "embedding-secret" not in first
    assert "llm-secret" not in first


def test_namespace_changes_with_history_and_structured_schema() -> None:
    class Invoice:
        pass

    initial = cache_namespace(_config())
    with_history = cache_namespace(_config(history=[{"role": "user", "content": "private turn"}]))
    with_schema = cache_namespace(_config(output_model=Invoice))
    assert len({initial, with_history, with_schema}) == 3
    assert "private turn" not in with_history


def test_namespace_tracks_graph_index_and_redacts_nested_vector_credentials() -> None:
    base = cache_namespace(_config(lightrag_working_dir="/var/lib/docpipe/graph-a"))
    other_index = cache_namespace(_config(lightrag_working_dir="/var/lib/docpipe/graph-b"))
    with_nested_secret = cache_namespace(
        _config(
            vector_store={
                "provider": "qdrant",
                "options": {"auth": {"password": "nested-private-value"}},
            }
        )
    )

    assert base != other_index
    assert "nested-private-value" not in with_nested_secret


def test_namespace_isolates_database_users_for_the_same_vector_endpoint() -> None:
    first = cache_namespace(
        _config(
            connection_string=None,
            vector_store={
                "provider": "pgvector",
                "options": {"dsn": "postgresql://reader_a:secret-a@db.internal:5432/docs"},
            },
        )
    )
    second = cache_namespace(
        _config(
            connection_string=None,
            vector_store={
                "provider": "pgvector",
                "options": {"dsn": "postgresql://reader_b:secret-b@db.internal:5432/docs"},
            },
        )
    )

    assert first != second
    assert "reader_a" not in first
    assert "secret-a" not in first


def test_opaque_key_isolated_by_question_tenant_and_retrieval_filter() -> None:
    config = _config()
    key = cache_key(config, "private question", tenant_scope="tenant-a")

    assert key != cache_key(config, "different question", tenant_scope="tenant-a")
    assert key != cache_key(config, "private question", tenant_scope="tenant-b")
    assert key != cache_key(
        _config(filters={"department": "finance"}),
        "private question",
        tenant_scope="tenant-a",
    )
    assert len(key) == 64
    assert "private question" not in key
    assert "tenant-a" not in key
