"""Tests for TurboVec generation persistence through a vendor-free fake index."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    Equals,
    VectorQuery,
    VectorRecord,
    WriteBatch,
)
from docpipe.plugins.errors import PluginCapabilityError, VectorStoreOperationError
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig
from docpipe.vectorstores.turbovec.persistence import INDEX_FILENAME
from docpipe.vectorstores.turbovec.repository import TurboVecFileRepository
from docpipe.vectorstores.turbovec.vendor import TurboVecIndex


class FakeIndex:
    """Small exact index implementing the adapter's structural vendor boundary."""

    def __init__(
        self,
        dim: int,
        bit_width: int,
        rows: dict[int, list[float]] | None = None,
    ) -> None:
        self.dim = dim
        self.bit_width = bit_width
        self.rows = rows or {}

    def __len__(self) -> int:
        return len(self.rows)

    def add_with_ids(self, vectors: object, ids: object) -> None:
        assert isinstance(vectors, list) and isinstance(ids, list)
        for vector, numeric_id in zip(vectors, ids, strict=True):
            assert isinstance(vector, list) and isinstance(numeric_id, int)
            self.rows[numeric_id] = [float(value) for value in vector]

    def remove(self, numeric_id: int) -> bool:
        return self.rows.pop(numeric_id, None) is not None

    def search(
        self, queries: object, k: int, *, allowlist: object | None = None
    ) -> tuple[object, object]:
        assert isinstance(queries, list) and isinstance(queries[0], list)
        query = queries[0]
        allowed = set(allowlist) if isinstance(allowlist, list) else set(self.rows)
        scored = sorted(
            (
                (sum(left * right for left, right in zip(query, vector, strict=True)), numeric_id)
                for numeric_id, vector in self.rows.items()
                if numeric_id in allowed
            ),
            key=lambda item: (-item[0], item[1]),
        )[:k]
        return FakeMatrix([[score for score, _ in scored]]), FakeMatrix(
            [[numeric_id for _, numeric_id in scored]]
        )

    def write(self, path: str) -> None:
        Path(path).write_text(
            json.dumps(
                {
                    "dim": self.dim,
                    "bit_width": self.bit_width,
                    "rows": {str(key): value for key, value in self.rows.items()},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )


class FakeMatrix(list[list[float | int]]):
    def tolist(self) -> list[list[float | int]]:
        return self


class FakeIndexFactory:
    def create(self, *, dimensions: int, bit_width: int) -> TurboVecIndex:
        return FakeIndex(dimensions, bit_width)

    def load(self, path: Path) -> TurboVecIndex:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return FakeIndex(
            int(raw["dim"]),
            int(raw["bit_width"]),
            {int(key): value for key, value in raw["rows"].items()},
        )

    def vectors(self, rows: Sequence[Sequence[object]]) -> object:
        return [[float(value) for value in row] for row in rows]

    def ids(self, values: Sequence[int]) -> object:
        return list(values)


def _repository(tmp_path: Path) -> TurboVecFileRepository:
    return TurboVecFileRepository(
        TurboVecConfig(index_root=tmp_path),
        index_factory=FakeIndexFactory(),
    )


def test_repository_round_trip_filter_aggregation_and_delete(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    collection = CollectionRef("documents")
    repository.ensure_collection(collection, 8)
    records = (
        VectorRecord(
            "invoice-2",
            "second",
            [0.5] * 8,
            {"tenant": "beta"},
            "b.pdf",
        ),
        VectorRecord(
            "invoice-1",
            "first",
            [1.0] * 8,
            {"tenant": "acme"},
            "a.pdf",
        ),
        VectorRecord(
            "invoice-3",
            "third",
            [0.25] * 8,
            {"tenant": "acme"},
            "a.pdf",
        ),
    )

    assert repository.upsert(WriteBatch(collection, records)) == 3
    matches = repository.search(
        VectorQuery(
            collection,
            dense_vector=[1.0] * 8,
            filter=Equals("tenant", "acme"),
            limit=5,
        )
    )

    assert [match.record_id for match in matches] == ["invoice-1", "invoice-3"]
    aggregates = repository.aggregate_sources(collection)
    assert [(item.source_id, item.record_count) for item in aggregates] == [
        ("a.pdf", 2),
        ("b.pdf", 1),
    ]
    assert repository.delete_by_source(collection, "a.pdf") == 2
    assert repository.delete_by_source(collection, "a.pdf") == 0
    assert [item.source_id for item in repository.aggregate_sources(collection)] == ["b.pdf"]


def test_repository_replaces_existing_record_without_duplicate(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    collection = CollectionRef("documents")
    repository.ensure_collection(collection, 8)

    repository.upsert(
        WriteBatch(collection, (VectorRecord("same", "old", [0.1] * 8, source_id="old"),))
    )
    repository.upsert(
        WriteBatch(collection, (VectorRecord("same", "new", [0.2] * 8, source_id="new"),))
    )

    aggregates = repository.aggregate_sources(collection)
    assert [(item.source_id, item.record_count) for item in aggregates] == [("new", 1)]


def test_repository_rejects_sparse_queries_explicitly(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    collection = CollectionRef("documents")
    repository.ensure_collection(collection, 8)

    with pytest.raises(PluginCapabilityError):
        repository.search(VectorQuery(collection, sparse_vector={1: 0.5}))


def test_repository_detects_index_tampering_without_leaking_content(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    collection = CollectionRef("documents")
    repository.ensure_collection(collection, 8)
    index_path = tmp_path / collection.name / INDEX_FILENAME
    index_path.write_text("private-corrupt-index", encoding="utf-8")

    with pytest.raises(VectorStoreOperationError, match="corrupt") as caught:
        repository.aggregate_sources(collection)

    assert "private-corrupt-index" not in str(caught.value.to_dict())
