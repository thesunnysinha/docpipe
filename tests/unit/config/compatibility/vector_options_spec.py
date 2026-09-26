"""Vector-store option translation and safe secret references."""

from __future__ import annotations

import pytest

from docpipe.config.compatibility import resolve_vector_options
from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.core.errors import ConfigurationError


def should_map_legacy_vector_fields_to_namespaced_options() -> None:
    pg = resolve_vector_options(
        provider="pgvector",
        connection_string="postgresql://user:password@db/docs",
        collection="docs",
    )
    turbo = resolve_vector_options(
        provider="turbovec",
        connection_string="postgresql://unused/db",
        collection="docs",
        index_root="/indices",
        bit_width=3,
    )
    assert pg == VectorStoreOptions(
        provider="pgvector",
        options={"dsn": "postgresql://user:password@db/docs", "collection": "docs"},
    )
    assert turbo == VectorStoreOptions(
        provider="turbovec",
        options={"index_root": "/indices", "collection": "docs", "bit_width": 3},
    )


def should_accept_agreement_and_reject_explicit_legacy_conflicts() -> None:
    supplied = VectorStoreOptions(
        provider="pgvector",
        options={"dsn": "postgresql://db/docs", "collection": "docs", "connect_timeout_seconds": 2},
    )
    resolved = resolve_vector_options(
        provider="pgvector",
        connection_string="postgresql://db/docs",
        collection="docs",
        namespaced=supplied,
        explicit_legacy=frozenset({"vector_backend", "connection_string", "table_name"}),
    )
    assert resolved == supplied
    with pytest.raises(ConfigurationError, match="connection_string"):
        resolve_vector_options(
            provider="pgvector",
            connection_string="postgresql://other/db",
            collection="docs",
            namespaced=supplied,
            explicit_legacy=frozenset({"connection_string"}),
        )
    with pytest.raises(ConfigurationError, match="vector_backend"):
        resolve_vector_options(
            provider="turbovec",
            connection_string="ignored",
            collection="docs",
            namespaced=supplied,
            explicit_legacy=frozenset({"vector_backend"}),
        )


def should_not_resolve_secret_references_during_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QDRANT_SECRET", "actual-secret-must-not-appear")
    supplied = VectorStoreOptions(
        provider="qdrant",
        options={"api_key_ref": "env://QDRANT_SECRET", "url": "https://vectors.example"},
    )
    resolved = resolve_vector_options(
        provider="pgvector",
        connection_string=None,
        collection="docs",
        namespaced=supplied,
    )
    serialized = resolved.model_dump_json()
    assert resolved.provider == "qdrant"
    assert "env://QDRANT_SECRET" in serialized
    assert "actual-secret-must-not-appear" not in serialized
