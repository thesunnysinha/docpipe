"""Vendor-neutral source resolver protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.plugins.contracts.source.handle import ResolvedSourceHandle


@runtime_checkable
class SourceResolver(Protocol):
    """Discover support without I/O and safely resolve source content."""

    def supports(self, source: str) -> bool:
        """Return whether this resolver recognizes a URI scheme."""
        ...

    async def resolve(self, source: str) -> ResolvedSourceHandle:
        """Return an owned context handle after safe source validation."""
        ...
