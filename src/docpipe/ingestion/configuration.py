"""Immutable options for vendor-neutral ingestion orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from docpipe.plugins.contracts.vectorstore import CollectionRef
from docpipe.plugins.contracts.vectorstore.values import FrozenJson, freeze_metadata


class IngestMode(str, Enum):
    """Document representations selected for ingestion."""

    CHUNKS = "chunks"
    EXTRACTIONS = "extractions"
    BOTH = "both"


class IncrementalFailureMode(str, Enum):
    """Behavior when incremental state cannot be checked safely."""

    FAIL_CLOSED = "fail_closed"
    LEGACY_BEST_EFFORT = "legacy_best_effort"


@dataclass(frozen=True, slots=True)
class IngestionOptions:
    """Per-operation limits and behavior, detached from global settings."""

    collection: CollectionRef
    batch_size: int = 64
    max_in_flight: int = 4
    incremental: bool = False
    incremental_failure_mode: IncrementalFailureMode = IncrementalFailureMode.FAIL_CLOSED
    chunk_metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate limits and freeze caller-owned metadata."""
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least one")
        if self.max_in_flight < 1:
            raise ValueError("max_in_flight must be at least one")
        frozen: Mapping[str, FrozenJson] = freeze_metadata(self.chunk_metadata)
        object.__setattr__(self, "chunk_metadata", frozen)
