"""Tests for pgvector plugin configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docpipe.vectorstores.pgvector.configuration import PgVectorConfig


def test_configuration_masks_dsn_and_accepts_legacy_boundary() -> None:
    config = PgVectorConfig.from_legacy(
        connection_string="postgresql://admin:secret@db/docpipe",
        table_name="documents",
    )

    assert "secret" not in repr(config)
    assert config.dsn.get_secret_value().endswith("/docpipe")
    assert config.default_collection.name == "documents"


def test_configuration_rejects_unknown_options_and_unsafe_collection() -> None:
    with pytest.raises(ValidationError):
        PgVectorConfig(dsn="postgresql://db/docpipe", collection="bad;drop")
    with pytest.raises(ValidationError):
        PgVectorConfig(dsn="postgresql://db/docpipe", unexpected=True)
