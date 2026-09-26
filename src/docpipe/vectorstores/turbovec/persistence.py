"""Atomic and schema-validated persistence for TurboVec collection snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

from docpipe.plugins.errors import VectorStoreOperationError

DOCSTORE_VERSION = 1
INDEX_FILENAME = "index.tvim"
DOCSTORE_FILENAME = "docstore.json"
MAX_UINT64 = (1 << 64) - 1
DocstoreRecord = dict[str, object]
Docstore = dict[int, DocstoreRecord]


@dataclass(frozen=True, slots=True)
class DocstoreSnapshot:
    """Validated record metadata paired with an optional index digest."""

    records: Docstore
    index_sha256: str | None = None


def atomic_publish(target: Path, writer: Callable[[Path], None]) -> None:
    """Publish a directory generation while preserving the prior generation.

    ``writer`` receives an empty temporary sibling directory. If it raises, the
    previous target remains untouched. A successful write is swapped into place;
    a failed swap restores the previous directory before propagating the error.

    Args:
        target: Final collection directory.
        writer: Callback that completely populates the staging directory.

    Raises:
        OSError: If staging, replacement, restoration, or cleanup fails.
        Exception: Any exception raised by ``writer`` after staging cleanup.
    """
    target = target.resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(mkdtemp(prefix=f".{target.name}-staging-", dir=target.parent))
    backup = target.with_name(f".{target.name}-backup-{uuid4().hex}")
    moved_previous = False
    try:
        writer(staging)
        if target.exists():
            os.replace(target, backup)
            moved_previous = True
        try:
            os.replace(staging, target)
        except Exception:
            if moved_previous and backup.exists() and not target.exists():
                os.replace(backup, target)
            raise
        if moved_previous:
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        # A backup remains only when replacement succeeded but cleanup failed.
        # Keep it as a recoverable generation rather than risking data loss.


def write_docstore(
    path: Path,
    records: Mapping[int, Mapping[str, object]],
    *,
    index_sha256: str | None = None,
) -> None:
    """Atomically write a canonical, versioned Docpipe record store."""
    normalized = _validate_records(records)
    payload: dict[str, object] = {
        "version": DOCSTORE_VERSION,
        "records": {str(key): normalized[key] for key in sorted(normalized)},
    }
    if index_sha256 is not None:
        if not _is_sha256(index_sha256):
            raise ValueError("index_sha256 must be a lowercase SHA-256 digest")
        payload["index_sha256"] = index_sha256
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}-{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_docstore(path: Path) -> Docstore:
    """Read records from a validated versioned docstore.

    Raises:
        VectorStoreOperationError: If the file is missing, malformed, or corrupt.
    """
    return read_docstore_snapshot(path).records


def read_docstore_snapshot(path: Path) -> DocstoreSnapshot:
    """Read records and integrity metadata without exposing malformed content."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("version") != DOCSTORE_VERSION:
            raise ValueError("unsupported docstore envelope")
        records_value = raw.get("records")
        if not isinstance(records_value, dict):
            raise ValueError("docstore records must be an object")
        parsed: dict[int, Mapping[str, object]] = {}
        for key, value in records_value.items():
            if not isinstance(key, str) or not key.isdecimal() or not isinstance(value, dict):
                raise ValueError("invalid docstore record")
            parsed[int(key)] = value
        records = _validate_records(parsed)
        digest = raw.get("index_sha256")
        if digest is not None and (not isinstance(digest, str) or not _is_sha256(digest)):
            raise ValueError("invalid docstore digest")
        return DocstoreSnapshot(records, digest)
    except VectorStoreOperationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise VectorStoreOperationError(
            "TurboVec docstore is corrupt or unreadable",
            context={"provider": "turbovec", "component": "docstore"},
        ) from exc


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for one persisted index file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _validate_records(records: Mapping[int, Mapping[str, object]]) -> Docstore:
    normalized: Docstore = {}
    for numeric_id, record in records.items():
        if isinstance(numeric_id, bool) or not 0 <= numeric_id <= MAX_UINT64:
            raise ValueError("docstore IDs must be unsigned 64-bit integers")
        record_id = record.get("record_id")
        text = record.get("text")
        metadata = record.get("metadata")
        source_id = record.get("source_id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("docstore record_id must be a non-empty string")
        if not isinstance(text, str) or not isinstance(metadata, Mapping):
            raise ValueError("docstore record fields are invalid")
        if source_id is not None and not isinstance(source_id, str):
            raise ValueError("docstore source_id must be a string or null")
        plain_metadata = _plain_json_object(metadata)
        normalized[numeric_id] = {
            "record_id": record_id,
            "text": text,
            "metadata": plain_metadata,
            "source_id": source_id,
        }
    return normalized


def _plain_json_object(value: Mapping[object, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError("metadata keys must be strings")
        result[key] = _plain_json(item)
    return result


def _plain_json(value: object) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        return _plain_json_object(value)
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    raise ValueError("metadata must contain JSON-compatible values")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
