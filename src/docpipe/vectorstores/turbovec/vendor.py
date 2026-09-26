"""Lazy, narrow translation layer for the optional TurboVec and NumPy APIs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

from docpipe.plugins.errors import PluginDependencyError


class TurboVecIndex(Protocol):
    """Structural subset of ``turbovec.IdMapIndex`` used by Docpipe."""

    @property
    def dim(self) -> int | None:
        """Return vector dimensionality, when exposed by the index."""
        ...

    def __len__(self) -> int: ...

    def add_with_ids(self, vectors: object, ids: object) -> None:
        """Add dense vectors under caller-provided stable numeric identifiers."""
        ...

    def remove(self, numeric_id: int) -> bool:
        """Remove one numeric identifier and report whether it was present."""
        ...

    def search(
        self, queries: object, k: int, *, allowlist: object | None = None
    ) -> tuple[object, object]:
        """Return distance and identifier matrices for up to ``k`` neighbors."""
        ...

    def write(self, path: str) -> None:
        """Serialize the complete index to the supplied filesystem path."""
        ...


class TurboVecIndexFactory(Protocol):
    """Construction seam that makes the vendor boundary independently testable."""

    def create(self, *, dimensions: int, bit_width: int) -> TurboVecIndex:
        """Create an empty index with fixed dimensions and quantization width."""
        ...

    def load(self, path: Path) -> TurboVecIndex:
        """Load a persisted index from a path managed by the repository."""
        ...

    def vectors(self, rows: Sequence[Sequence[object]]) -> object:
        """Convert vector rows into the contiguous numeric layout the vendor needs."""
        ...

    def ids(self, values: Sequence[int]) -> object:
        """Convert stable record IDs into the vendor's identifier array type."""
        ...


class _IndexConstructor(Protocol):
    def __call__(self, *, dim: int, bit_width: int) -> object: ...

    def load(self, path: str) -> object:
        """Load a vendor index from its serialized path."""
        ...


class _NumpyModule(Protocol):
    float32: object
    uint64: object

    def ascontiguousarray(self, value: object, *, dtype: object) -> object:
        """Return a contiguous array with the requested numeric dtype."""
        ...

    def asarray(self, value: object, *, dtype: object) -> object:
        """Convert input values into an array using the requested dtype."""
        ...


class LazyTurboVecIndexFactory:
    """Load optional packages only after TurboVec is selected and used."""

    def create(self, *, dimensions: int, bit_width: int) -> TurboVecIndex:
        """Create an empty stable-ID index."""
        index_type, _ = self._dependencies()
        return cast(TurboVecIndex, index_type(dim=dimensions, bit_width=bit_width))

    def load(self, path: Path) -> TurboVecIndex:
        """Load a stable-ID index from disk."""
        index_type, _ = self._dependencies()
        return cast(TurboVecIndex, index_type.load(str(path)))

    def vectors(self, rows: Sequence[Sequence[object]]) -> object:
        """Convert dense rows to contiguous float32 storage."""
        _, numpy = self._dependencies()
        return numpy.ascontiguousarray(rows, dtype=numpy.float32)

    def ids(self, values: Sequence[int]) -> object:
        """Convert stable IDs to unsigned 64-bit storage."""
        _, numpy = self._dependencies()
        return numpy.asarray(values, dtype=numpy.uint64)

    @staticmethod
    def _dependencies() -> tuple[_IndexConstructor, _NumpyModule]:
        try:
            import numpy
            from turbovec import IdMapIndex
        except ImportError as exc:
            raise PluginDependencyError(
                "TurboVec dependency is unavailable",
                plugin="turbovec",
                hint="Install with: pip install 'docpipe-sdk[turbovec]'",
            ) from exc
        return cast(_IndexConstructor, IdMapIndex), cast(_NumpyModule, numpy)
