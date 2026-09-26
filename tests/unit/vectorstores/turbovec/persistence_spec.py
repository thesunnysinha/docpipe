"""Tests for atomic TurboVec index and docstore persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from docpipe.plugins.errors import VectorStoreOperationError
from docpipe.vectorstores.turbovec.persistence import atomic_publish, read_docstore, write_docstore


def test_atomic_publish_preserves_previous_directory_on_writer_failure(tmp_path: Path) -> None:
    target = tmp_path / "documents"
    target.mkdir()
    (target / "index.tvim").write_text("previous", encoding="utf-8")

    def broken(staging: Path) -> None:
        (staging / "index.tvim").write_text("partial", encoding="utf-8")
        raise RuntimeError("disk full")

    with pytest.raises(RuntimeError, match="disk full"):
        atomic_publish(target, broken)

    assert (target / "index.tvim").read_text(encoding="utf-8") == "previous"
    assert not tuple(tmp_path.glob(".documents-staging-*"))


def test_docstore_round_trip_and_safe_corruption_error(tmp_path: Path) -> None:
    path = tmp_path / "docstore.json"
    write_docstore(path, {7: {"record_id": "doc-7", "text": "hello", "metadata": {}}})

    assert read_docstore(path)[7]["record_id"] == "doc-7"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(VectorStoreOperationError, match="corrupt") as caught:
        read_docstore(path)
    assert "not-json" not in str(caught.value.to_dict())
