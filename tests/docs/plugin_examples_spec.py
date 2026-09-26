"""Published plugin examples use only stable public imports."""

from __future__ import annotations

import json
from pathlib import Path

from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.testing import assert_source_conformance, assert_vector_store_conformance


def test_public_conformance_exports_exist() -> None:
    assert callable(assert_vector_store_conformance)
    assert callable(assert_source_conformance)


def test_documented_vector_envelope_is_valid_json_and_schema() -> None:
    docs = Path(__file__).resolve().parents[2] / "docs" / "plugins" / "configuration.md"
    snippet = docs.read_text(encoding="utf-8").split("```json\n", 1)[1].split("\n```", 1)[0]
    envelope = json.loads(snippet)

    selected = VectorStoreOptions.model_validate(envelope["vector_store"])

    assert selected.provider == "pgvector"
    assert selected.options["collection"] == "documents"
