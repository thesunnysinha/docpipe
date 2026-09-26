"""Namespaced plugin option envelopes remain transport safe."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docpipe.config.plugin_options import SourcePluginOptions, VectorStoreOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import IngestionConfig, RAGConfig
from docpipe.schemas.ingest import IngestRequest
from docpipe.schemas.rag import RAGQueryRequest
from docpipe.schemas.search import SearchRequest
from docpipe.server.app import create_app


def test_vector_and_source_options_are_immutable_json_envelopes() -> None:
    vector = VectorStoreOptions(
        provider="qdrant",
        options={"url": "https://vectors.example", "collection": "docs"},
    )
    source = SourcePluginOptions(
        provider="s3",
        options={"allowed_buckets": ["reports"]},
    )

    assert vector.model_dump()["provider"] == "qdrant"
    assert source.model_dump()["options"] == {"allowed_buckets": ["reports"]}
    with pytest.raises(ValidationError):
        VectorStoreOptions(provider="arbitrary.Class", options={})
    with pytest.raises(ValidationError):
        SourcePluginOptions(provider="s3", options={"client": object()})


def test_internal_ingestion_and_rag_configs_accept_new_provider_names() -> None:
    vector = VectorStoreOptions(provider="qdrant", options={"collection": "docs"})
    ingestion = IngestionConfig(
        connection_string="postgresql://legacy/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="model",
        vector_store=vector,
    )
    rag = RAGConfig(
        connection_string="postgresql://legacy/db",
        table_name="docs",
        embedding_provider="openai",
        embedding_model="model",
        llm_provider="openai",
        llm_model="model",
        vector_store=vector,
    )

    assert ingestion.vector_store == vector
    assert rag.vector_store == vector
    assert ingestion.vector_backend is None


def test_public_request_schemas_and_openapi_expose_namespaced_fields() -> None:
    new_vector = {"provider": "qdrant", "options": {"url": "https://vectors.example"}}
    ingested = IngestRequest.model_validate(
        {
            "source": "s3://reports/one.pdf",
            "connection_string": "legacy-unused",
            "table_name": "docs",
            "embedding_provider": "openai",
            "embedding_model": "model",
            "vector_store": new_vector,
            "source_plugin": {"provider": "s3", "options": {"allowed_buckets": ["reports"]}},
        }
    )
    assert ingested.vector_store is not None
    assert ingested.vector_store.provider == "qdrant"
    assert ingested.source_plugin is not None
    assert ingested.source_plugin.provider == "s3"

    schema = create_app().openapi()["components"]["schemas"]
    assert "vector_store" in schema["IngestRequest"]["properties"]
    assert "source_plugin" in schema["IngestRequest"]["properties"]
    assert "vector_store" in schema["SearchRequest"]["properties"]
    assert "vector_store" in schema["RAGQueryRequest"]["properties"]
    assert "vector_backend" in schema["IngestRequest"]["properties"]
    assert "connection_string" in schema["SearchRequest"]["properties"]
    assert SearchRequest.model_fields["vector_store"].annotation is not None
    assert RAGQueryRequest.model_fields["vector_store"].annotation is not None


def test_new_vector_provider_does_not_require_legacy_dsn_field() -> None:
    shared = {
        "table_name": "docs",
        "embedding_provider": "openai",
        "embedding_model": "model",
        "vector_store": {
            "provider": "qdrant",
            "options": {"url": "https://vectors.example", "collection": "docs"},
        },
    }
    ingestion = IngestRequest.model_validate({**shared, "source": "/reports/one.pdf"})
    search = SearchRequest.model_validate({**shared, "query": "hello"})
    rag = RAGQueryRequest.model_validate(
        {
            **shared,
            "question": "hello",
            "llm_provider": "openai",
            "llm_model": "model",
            "system_prompt": "Answer {question} with {context}",
        }
    )

    assert ingestion.connection_string is None
    assert search.connection_string is None
    assert rag.connection_string is None


def test_process_settings_accept_namespaced_vector_provider_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCPIPE_VECTOR_STORE",
        '{"provider":"qdrant","options":{"url":"https://vectors.example"}}',
    )

    settings = DocpipeSettings()

    assert settings.vector_store is not None
    assert settings.vector_store.provider == "qdrant"
