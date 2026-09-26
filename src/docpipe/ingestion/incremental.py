"""Deterministic source fingerprints and explicit duplicate decisions."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from docpipe.core.types import ParsedDocument
from docpipe.ingestion.configuration import IncrementalFailureMode
from docpipe.ingestion.errors import IncrementalStateError as IncrementalStateError
from docpipe.plugins.contracts.vectorstore import CollectionRef, Equals, VectorQuery, VectorReader
from docpipe.plugins.contracts.vectorstore.values import freeze_metadata

_LOGGER = logging.getLogger(__name__)


class IncrementalState(Protocol):
    """Narrow lookup boundary for persisted content fingerprints."""

    async def contains(self, fingerprint: str) -> bool:
        """Return whether a complete prior write has this fingerprint."""
        ...


class QueryEncoder(Protocol):
    """Query-only subset of the embedding encoder port."""

    async def encode_query(self, text: str) -> tuple[float, ...]:
        """Encode a probe query for metadata-filtered lookup."""
        ...


class VectorIncrementalState:
    """Check fingerprint metadata through the vector reader facet."""

    def __init__(
        self,
        reader: VectorReader,
        encoder: QueryEncoder,
        collection: CollectionRef,
    ) -> None:
        self._reader = reader
        self._encoder = encoder
        self._collection = collection

    async def contains(self, fingerprint: str) -> bool:
        """Search one allowlisted fingerprint without accessing vendor APIs."""
        query_vector = await self._encoder.encode_query("")
        matches = await self._reader.search(
            VectorQuery(
                self._collection,
                dense_vector=query_vector,
                filter=Equals("source_hash", fingerprint),
                limit=1,
            )
        )
        return bool(matches)


class IncrementalDecider:
    """Apply fail-closed or explicitly requested legacy lookup behavior."""

    def __init__(
        self,
        state: IncrementalState,
        *,
        failure_mode: IncrementalFailureMode = IncrementalFailureMode.FAIL_CLOSED,
        logger: logging.Logger | None = None,
    ) -> None:
        self._state = state
        self._failure_mode = failure_mode
        self._logger = logger or _LOGGER

    async def should_skip(self, fingerprint: str) -> bool:
        """Return a duplicate decision or raise a safe state error."""
        try:
            return await self._state.contains(fingerprint)
        except Exception as exc:
            if self._failure_mode is IncrementalFailureMode.LEGACY_BEST_EFFORT:
                self._logger.warning(
                    "incremental.lookup.failed_open",
                    extra={
                        "event": "incremental.lookup.failed_open",
                        "error_code": "incremental_state_unavailable",
                    },
                )
                return False
            raise IncrementalStateError("incremental state lookup failed") from exc


def content_fingerprint(content: bytes, metadata: Mapping[str, object]) -> str:
    """Hash exact bytes plus canonical, validated metadata."""
    digest = hashlib.sha256()
    digest.update(b"docpipe-ingestion-v1\0")
    digest.update(content)
    digest.update(b"\0")
    digest.update(_canonical_metadata(metadata))
    return digest.hexdigest()


def parsed_document_fingerprint(parsed: ParsedDocument) -> str:
    """Fingerprint local source bytes when available, otherwise parsed UTF-8."""
    metadata: Mapping[str, object] = {
        "format": parsed.format.value,
        "metadata": parsed.metadata,
    }
    source_path = Path(parsed.source).expanduser()
    if source_path.is_file():
        digest = hashlib.sha256()
        digest.update(b"docpipe-ingestion-v1\0")
        with source_path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        digest.update(b"\0")
        digest.update(_canonical_metadata(metadata))
        return digest.hexdigest()
    return content_fingerprint(parsed.text.encode("utf-8"), metadata)


def _canonical_metadata(metadata: Mapping[str, object]) -> bytes:
    frozen = freeze_metadata(metadata)
    plain = _plain_json(frozen)
    return json.dumps(plain, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value
