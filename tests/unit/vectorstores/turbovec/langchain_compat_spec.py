"""Tests for the deprecated TurboVec LangChain compatibility boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from docpipe.vectorstores.turbovec_store import load_or_create_turbovec_store


def should_use_the_embedding_parameter_supported_by_turbovec_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TurboVecOneStore:
        def __init__(self, *, embedding: object, bit_width: int) -> None:
            self.embedding = embedding
            self.bit_width = bit_width

    monkeypatch.setattr(
        "docpipe.vectorstores.turbovec_store._import_turbovec_langchain",
        lambda: TurboVecOneStore,
    )
    embeddings = object()

    store = load_or_create_turbovec_store(
        embeddings=embeddings,
        table_name="documents",
        index_dir=tmp_path,
        bit_width=3,
    )

    assert store.embedding is embeddings
    assert store.bit_width == 3
