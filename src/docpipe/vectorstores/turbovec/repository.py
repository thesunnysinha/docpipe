"""Thread-safe generation-based persistence for local TurboVec collections."""

from __future__ import annotations

import hashlib
import os
import shutil
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeVar, cast

from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorMatch,
    VectorQuery,
    VectorRecord,
    WriteBatch,
)
from docpipe.plugins.errors import (
    CollectionNotFoundError,
    PluginCapabilityError,
    PluginDependencyError,
    VectorStoreOperationError,
)
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig
from docpipe.vectorstores.turbovec.filters import matches_filter
from docpipe.vectorstores.turbovec.persistence import (
    DOCSTORE_FILENAME,
    INDEX_FILENAME,
    Docstore,
    atomic_publish,
    read_docstore_snapshot,
    sha256_file,
    write_docstore,
)
from docpipe.vectorstores.turbovec.vendor import (
    LazyTurboVecIndexFactory,
    TurboVecIndex,
    TurboVecIndexFactory,
)

Numeric = TypeVar("Numeric", int, float)


class TurboVecFileRepository:
    """Persist TurboVec indexes and Docpipe records as atomic generations.

    Calls are thread-safe within one process. TurboVec permits only one process
    writing a path, so shared roots require coordination outside this adapter.
    """

    def __init__(
        self,
        config: TurboVecConfig,
        *,
        index_factory: TurboVecIndexFactory | None = None,
    ) -> None:
        self._config = config
        self._indexes = index_factory or LazyTurboVecIndexFactory()
        self._lock = threading.RLock()

    def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Create an empty collection or verify its existing dimensions."""
        self._config.validate_dimensions(dimensions)
        with self._lock:
            self._ensure_writable_root()
            target = self._config.collection_path(collection)
            if target.exists():
                index, _ = self._load(collection)
                if index.dim != dimensions:
                    raise ValueError("collection already exists with different dimensions")
                return
            index = self._indexes.create(
                dimensions=dimensions,
                bit_width=self._config.bit_width,
            )
            self._publish(target, index, {})

    def delete_collection(self, collection: CollectionRef) -> None:
        """Delete a collection directory if it exists."""
        with self._lock:
            target = self._config.collection_path(collection)
            if target.exists():
                shutil.rmtree(target)

    def upsert(self, batch: WriteBatch) -> int:
        """Atomically replace records by stable Docpipe record identifier."""
        with self._lock:
            index, records = self._load(batch.collection)
            dimensions = index.dim
            if dimensions is None:
                raise VectorStoreOperationError(
                    "TurboVec index has invalid dimensions",
                    context={"provider": "turbovec"},
                )
            latest = {record.record_id: record for record in batch.records}
            numeric_ids: list[int] = []
            vectors: list[Sequence[object]] = []
            for record_id in sorted(latest):
                record = latest[record_id]
                if len(record.vector) != dimensions:
                    raise ValueError("record vector dimensions do not match collection")
                numeric_id = _stable_numeric_id(record.record_id, records)
                if numeric_id in records:
                    index.remove(numeric_id)
                records[numeric_id] = _stored_record(record)
                numeric_ids.append(numeric_id)
                vectors.append(record.vector)
            index.add_with_ids(self._indexes.vectors(vectors), self._indexes.ids(numeric_ids))
            self._publish(self._config.collection_path(batch.collection), index, records)
            return len(batch.records)

    def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Search dense vectors, applying typed metadata filters as an allowlist."""
        if query.dense_vector is None or query.sparse_vector is not None:
            raise PluginCapabilityError(
                "TurboVec adapter requires a dense query vector",
                plugin="turbovec",
            )
        with self._lock:
            index, records = self._load(query.collection)
            if index.dim is None or len(query.dense_vector) != index.dim:
                raise ValueError("query vector dimensions do not match collection")
            allowed = [
                numeric_id
                for numeric_id, record in records.items()
                if matches_filter(_metadata(record), query.filter)
            ]
            if not allowed or len(index) == 0:
                return ()
            scores, ids = index.search(
                self._indexes.vectors((query.dense_vector,)),
                min(query.limit, len(allowed)),
                allowlist=self._indexes.ids(allowed),
            )
            score_values = _first_matrix_row(scores, expected=float)
            id_values = _first_matrix_row(ids, expected=int)
            matches = tuple(
                _vector_match(numeric_id, score, records)
                for score, numeric_id in zip(score_values, id_values, strict=True)
            )
            return tuple(sorted(matches, key=lambda item: (-item.score, item.record_id)))

    def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete exact source matches and atomically publish the new generation."""
        with self._lock:
            index, records = self._load(collection)
            deleted_ids = sorted(
                numeric_id
                for numeric_id, record in records.items()
                if record.get("source_id") == source_id
            )
            if not deleted_ids:
                return 0
            for numeric_id in deleted_ids:
                index.remove(numeric_id)
                records.pop(numeric_id)
            self._publish(self._config.collection_path(collection), index, records)
            return len(deleted_ids)

    def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Return deterministic counts for every non-null source identifier."""
        with self._lock:
            _, records = self._load(collection)
            counts: dict[str, int] = {}
            for record in records.values():
                source_id = record.get("source_id")
                if isinstance(source_id, str):
                    counts[source_id] = counts.get(source_id, 0) + 1
            return tuple(SourceAggregate(key, counts[key]) for key in sorted(counts))

    def health(self) -> bool:
        """Return whether the configured root or its parent is locally writable."""
        root = self._config.index_root
        candidate = root if root.exists() else root.parent
        return candidate.is_dir() and os.access(candidate, os.R_OK | os.W_OK | os.X_OK)

    def _ensure_writable_root(self) -> None:
        self._config.index_root.mkdir(parents=True, exist_ok=True)
        if not self.health():
            raise PermissionError("TurboVec index root is not writable")

    def _load(self, collection: CollectionRef) -> tuple[TurboVecIndex, Docstore]:
        target = self._config.collection_path(collection)
        if not target.is_dir():
            raise CollectionNotFoundError(
                "vector collection was not found",
                context={"collection": collection.name},
            )
        index_path = target / INDEX_FILENAME
        snapshot = read_docstore_snapshot(target / DOCSTORE_FILENAME)
        try:
            if snapshot.index_sha256 is None or sha256_file(index_path) != snapshot.index_sha256:
                raise ValueError("index digest mismatch")
            index = self._indexes.load(index_path)
        except PluginDependencyError:
            raise
        except (OSError, TypeError, ValueError) as exc:
            raise VectorStoreOperationError(
                "TurboVec index is corrupt or unreadable",
                context={"provider": "turbovec", "component": "index"},
            ) from exc
        if len(index) != len(snapshot.records):
            raise VectorStoreOperationError(
                "TurboVec index and docstore are inconsistent",
                context={"provider": "turbovec", "component": "snapshot"},
            )
        return index, dict(snapshot.records)

    @staticmethod
    def _publish(target: Path, index: TurboVecIndex, records: Docstore) -> None:
        def write_generation(staging: Path) -> None:
            index_path = staging / INDEX_FILENAME
            index.write(str(index_path))
            write_docstore(
                staging / DOCSTORE_FILENAME,
                records,
                index_sha256=sha256_file(index_path),
            )

        atomic_publish(target, write_generation)


def _stable_numeric_id(record_id: str, records: Mapping[int, Mapping[str, object]]) -> int:
    for attempt in range(256):
        digest = hashlib.blake2b(digest_size=8, person=b"docpipe")
        digest.update(record_id.encode("utf-8"))
        digest.update(attempt.to_bytes(2, "big"))
        numeric_id = int.from_bytes(digest.digest(), "big")
        existing = records.get(numeric_id)
        if existing is None or existing.get("record_id") == record_id:
            return numeric_id
    raise VectorStoreOperationError(
        "could not allocate a stable TurboVec record identifier",
        context={"provider": "turbovec"},
    )


def _stored_record(record: VectorRecord) -> dict[str, object]:
    return {
        "record_id": record.record_id,
        "text": record.text,
        "metadata": record.metadata,
        "source_id": record.source_id,
    }


def _metadata(record: Mapping[str, object]) -> Mapping[str, object]:
    value = record.get("metadata")
    return value if isinstance(value, Mapping) else {}


def _vector_match(
    numeric_id: int,
    score: float,
    records: Mapping[int, Mapping[str, object]],
) -> VectorMatch:
    record = records.get(numeric_id)
    if record is None:
        raise VectorStoreOperationError(
            "TurboVec returned an unknown record identifier",
            context={"provider": "turbovec"},
        )
    record_id = record.get("record_id")
    text = record.get("text")
    source_id = record.get("source_id")
    if not isinstance(record_id, str) or not isinstance(text, str):
        raise VectorStoreOperationError(
            "TurboVec docstore record is invalid",
            context={"provider": "turbovec"},
        )
    return VectorMatch(
        record_id=record_id,
        score=score,
        text=text,
        metadata=_metadata(record),
        source_id=source_id if isinstance(source_id, str) else None,
    )


def _first_matrix_row(value: object, *, expected: type[Numeric]) -> list[Numeric]:
    to_list = getattr(value, "tolist", None)
    converted = to_list() if callable(to_list) else value
    if not isinstance(converted, list) or not converted or not isinstance(converted[0], list):
        raise ValueError("TurboVec returned an invalid search result")
    row = converted[0]
    if not all(isinstance(item, expected) and not isinstance(item, bool) for item in row):
        raise ValueError("TurboVec returned an invalid search value")
    return [cast(Numeric, item) for item in row]
