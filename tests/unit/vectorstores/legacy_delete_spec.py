"""Compatibility routing tests for legacy vector deletion."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from docpipe.core.errors import ConfigurationError
from docpipe.vectorstores.factory import delete_legacy_source


def should_create_embeddings_only_for_turbovec() -> None:
    with (
        patch("docpipe.ingestion.legacy.create_embeddings") as create_embeddings,
        patch("docpipe.vectorstores.factory.delete_by_source", return_value=2) as delete,
    ):
        create_embeddings.return_value = object()

        deleted = delete_legacy_source(
            connection_string="postgresql://user:secret@localhost/docpipe",
            table_name="documents",
            vector_backend="turbovec",
            embedding_provider="openai",
            embedding_model="text-embedding-test",
            turbovec_index_dir="/tmp/docpipe-test-index",
            source="report.pdf",
            match_mode="exact",
        )

    assert deleted == 2
    create_embeddings.assert_called_once()
    assert delete.call_args.kwargs["embeddings"] is create_embeddings.return_value
    assert delete.call_args.kwargs["vector_backend"] == "turbovec"


def should_delete_pgvector_metadata_without_embeddings() -> None:
    with (
        patch("docpipe.ingestion.legacy.create_embeddings") as create_embeddings,
        patch("docpipe.vectorstores.factory.delete_by_source", return_value=1) as delete,
    ):
        deleted = delete_legacy_source(
            connection_string="postgresql://user:secret@localhost/docpipe",
            table_name="documents",
            vector_backend="pgvector",
            source_contains="reports/",
            match_mode="contains",
        )

    assert deleted == 1
    create_embeddings.assert_not_called()
    assert delete.call_args.kwargs["embeddings"] is None
    assert delete.call_args.kwargs["source_contains"] == "reports/"


def should_require_embedding_configuration_for_turbovec() -> None:
    with (
        patch("docpipe.ingestion.legacy.create_embeddings") as create_embeddings,
        pytest.raises(ConfigurationError, match="embedding_provider and embedding_model"),
    ):
        delete_legacy_source(
            connection_string="postgresql://user:secret@localhost/docpipe",
            table_name="documents",
            vector_backend="turbovec",
            source="report.pdf",
        )

    create_embeddings.assert_not_called()
