"""Immutable vendor-neutral vector-store records and queries."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

from docpipe.plugins.contracts.vectorstore.filters import FilterExpression, is_filter
from docpipe.plugins.contracts.vectorstore.values import (
    freeze_metadata,
    normalize_vector,
    validate_number,
)

_COLLECTION_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,62}")


@dataclass(frozen=True, slots=True)
class CollectionRef:
    """Validated logical collection identifier."""

    name: str

    def __post_init__(self) -> None:
        """Reject identifiers unsafe for vendor adapters."""
        if _COLLECTION_NAME.fullmatch(self.name) is None:
            raise ValueError("collection name must contain only safe identifier characters")


class VectorQueryKind(str, Enum):
    """Vector representation used by a query."""

    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """One vectorized document fragment prepared for storage."""

    record_id: str
    text: str
    vector: Sequence[object]
    metadata: Mapping[str, object] = field(default_factory=dict)
    source_id: str | None = None

    def __post_init__(self) -> None:
        record_id = self.record_id.strip()
        if not record_id:
            raise ValueError("record_id must not be empty")
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        source_id = self.source_id.strip() if self.source_id is not None else None
        if source_id == "":
            raise ValueError("source_id must not be empty")
        object.__setattr__(self, "record_id", record_id)
        object.__setattr__(self, "vector", normalize_vector(self.vector))
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))
        object.__setattr__(self, "source_id", source_id)


@dataclass(frozen=True, slots=True)
class VectorQuery:
    """Dense, sparse, or hybrid similarity query."""

    collection: CollectionRef
    dense_vector: Sequence[object] | None = None
    sparse_vector: Mapping[int, float] | None = None
    filter: FilterExpression | None = None
    limit: int = 10

    def __post_init__(self) -> None:
        dense = (
            normalize_vector(self.dense_vector, field_name="dense vector")
            if self.dense_vector is not None
            else None
        )
        sparse = _normalize_sparse(self.sparse_vector) if self.sparse_vector is not None else None
        if dense is None and sparse is None:
            raise ValueError("vector query requires a dense or sparse vector")
        if self.filter is not None and not is_filter(self.filter):
            raise TypeError("filter must be a typed filter expression")
        if self.limit < 1:
            raise ValueError("query limit must be at least one")
        object.__setattr__(self, "dense_vector", dense)
        object.__setattr__(self, "sparse_vector", sparse)

    @property
    def kind(self) -> VectorQueryKind:
        """Return the query's vector representation."""
        if self.dense_vector is not None and self.sparse_vector is not None:
            return VectorQueryKind.HYBRID
        if self.dense_vector is not None:
            return VectorQueryKind.DENSE
        return VectorQueryKind.SPARSE


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """One scored vector search result."""

    record_id: str
    score: float
    text: str
    metadata: Mapping[str, object] = field(default_factory=dict)
    source_id: str | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.score):
            raise ValueError("match score must be finite")
        object.__setattr__(self, "metadata", freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class SourceAggregate:
    """Stored record count for one normalized source identifier."""

    source_id: str
    record_count: int

    def __post_init__(self) -> None:
        if not self.source_id.strip() or self.record_count < 0:
            raise ValueError("source aggregate values are invalid")


@dataclass(frozen=True, slots=True)
class WriteBatch:
    """Atomic group of records targeting one collection."""

    collection: CollectionRef
    records: tuple[VectorRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        if not self.records:
            raise ValueError("write batch records must not be empty")


@dataclass(frozen=True, slots=True)
class WriteBatchResult:
    """Complete accounting of a vector write attempt."""

    requested: int
    accepted: int = 0
    rejected: int = 0
    uncertain: int = 0

    def __post_init__(self) -> None:
        counts = (self.requested, self.accepted, self.rejected, self.uncertain)
        if any(value < 0 for value in counts):
            raise ValueError("write result counts must be non-negative")
        if self.accepted + self.rejected + self.uncertain != self.requested:
            raise ValueError("write result outcome counts must sum to requested")


def _normalize_sparse(vector: Mapping[int, float]) -> Mapping[int, float]:
    if not vector:
        raise ValueError("sparse vector must not be empty")
    normalized: dict[int, float] = {}
    for index, value in vector.items():
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("sparse vector indices must be non-negative integers")
        validate_number(value, field_name="sparse vector value")
        normalized[index] = float(value)
    return MappingProxyType(normalized)
