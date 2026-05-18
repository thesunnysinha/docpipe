"""File-backed turbovec index helpers (optional ``docpipe-sdk[turbovec]`` extra)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from docpipe.core.errors import ConfigurationError, IngestionError

logger = logging.getLogger(__name__)


def turbovec_index_path(index_dir: Path, table_name: str) -> Path:
    """Directory for one collection (``index.tvim`` + ``docstore.json``)."""
    return index_dir / table_name


def _import_turbovec_langchain() -> Any:
    try:
        from turbovec.langchain import TurboQuantVectorStore
    except ImportError as err:
        raise ConfigurationError(
            "vector_backend='turbovec' requires turbovec. "
            "Install with: pip install 'docpipe-sdk[turbovec]'"
        ) from err
    return TurboQuantVectorStore


def load_or_create_turbovec_store(
    *,
    embeddings: Any,
    table_name: str,
    index_dir: Path,
    bit_width: int = 4,
) -> Any:
    """Load an on-disk turbovec store or create an empty one."""
    TurboQuantVectorStore = _import_turbovec_langchain()
    path = turbovec_index_path(index_dir, table_name)
    index_file = path / "index.tvim"
    if index_file.exists():
        return TurboQuantVectorStore.load(str(path), embedding=embeddings)
    path.mkdir(parents=True, exist_ok=True)
    return TurboQuantVectorStore(embeddings=embeddings, bit_width=bit_width)


def persist_turbovec_store(store: Any, table_name: str, index_dir: Path) -> None:
    """Write ``index.tvim`` and ``docstore.json`` under the collection path."""
    path = turbovec_index_path(index_dir, table_name)
    path.mkdir(parents=True, exist_ok=True)
    store.dump(str(path))


def ingest_documents_turbovec(
    *,
    documents: list[Any],
    embeddings: Any,
    table_name: str,
    index_dir: Path,
    bit_width: int = 4,
) -> None:
    """Add LangChain documents to a turbovec index and persist to disk."""
    store = load_or_create_turbovec_store(
        embeddings=embeddings,
        table_name=table_name,
        index_dir=index_dir,
        bit_width=bit_width,
    )
    try:
        store.add_documents(documents)
        persist_turbovec_store(store, table_name, index_dir)
    except Exception as e:
        raise IngestionError(f"Failed to ingest into turbovec store: {e}") from e


def _docstore_entries(docstore_path: Path) -> list[tuple[str, dict[str, Any]]]:
    """Return (id, entry) pairs from turbovec's docstore.json."""
    if not docstore_path.exists():
        return []
    raw = json.loads(docstore_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        if "docstore" in raw and isinstance(raw["docstore"], dict):
            store = raw["docstore"]
        elif all(isinstance(v, dict) for v in raw.values()):
            store = raw
        else:
            store = raw.get("documents", raw)
    else:
        return []
    return [(str(doc_id), entry) for doc_id, entry in store.items()]


def _entry_matches_source(
    entry: dict[str, Any],
    *,
    source: str | None,
    source_contains: str | None,
    match_mode: str,
) -> bool:
    metadata = entry.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    doc_source = str(metadata.get("source", ""))
    if match_mode == "contains":
        needle = source_contains or ""
        return needle in doc_source
    return doc_source == (source or "")


def delete_by_source_turbovec(
    *,
    embeddings: Any,
    table_name: str,
    index_dir: Path,
    source: str | None = None,
    source_contains: str | None = None,
    match_mode: str = "exact",
) -> int:
    """Remove chunks whose metadata source matches; returns rows deleted."""
    path = turbovec_index_path(index_dir, table_name)
    docstore_path = path / "docstore.json"
    entries = _docstore_entries(docstore_path)
    ids_to_delete = [
        doc_id
        for doc_id, entry in entries
        if _entry_matches_source(
            entry,
            source=source,
            source_contains=source_contains,
            match_mode=match_mode,
        )
    ]
    if not ids_to_delete:
        return 0
    store = load_or_create_turbovec_store(
        embeddings=embeddings,
        table_name=table_name,
        index_dir=index_dir,
    )
    try:
        store.delete(ids_to_delete)
        persist_turbovec_store(store, table_name, index_dir)
    except Exception as e:
        raise IngestionError(f"Turbovec delete failed: {e}") from e
    return len(ids_to_delete)
