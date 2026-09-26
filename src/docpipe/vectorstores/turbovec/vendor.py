"""Lazy, narrow translation layer for the optional TurboVec and NumPy APIs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

from docpipe.plugins.errors import PluginDependencyError


class TurboVecIndex(Protocol):
    """Structural subset of ``turbovec.IdMapIndex`` used by Docpipe."""

    @property
    def dim(self) -> int | None: ...

    def __len__(self) -> int: ...

    def add_with_ids(self, vectors: object, ids: object) -> None: ...

    def remove(self, numeric_id: int) -> bool: ...

    def search(
        self, queries: object, k: int, *, allowlist: object | None = None
    ) -> tuple[object, object]: ...

    def write(self, path: str) -> None: ...


class TurboVecIndexFactory(Protocol):
    """Construction seam that makes the vendor boundary independently testable."""

    def create(self, *, dimensions: int, bit_width: int) -> TurboVecIndex: ...

    def load(self, path: Path) -> TurboVecIndex: ...

    def vectors(self, rows: Sequence[Sequence[object]]) -> object: ...

    def ids(self, values: Sequence[int]) -> object: ...


class _IndexConstructor(Protocol):
    def __call__(self, *, dim: int, bit_width: int) -> object: ...

    def load(self, path: str) -> object: ...


class _NumpyModule(Protocol):
    float32: object
    uint64: object

    def ascontiguousarray(self, value: object, *, dtype: object) -> object: ...

    def asarray(self, value: object, *, dtype: object) -> object: ...


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
