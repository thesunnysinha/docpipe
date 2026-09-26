"""Vendor-neutral source resolver protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docpipe.plugins.contracts.source.handle import ResolvedSourceHandle


@runtime_checkable
class SourceResolver(Protocol):
    """Common contract for source discovery and safe content resolution.

    Implementations should make :meth:`supports` a cheap, side-effect-free
    classification check. Security-sensitive validation belongs in
    :meth:`resolve` and at the returned handle's actual read/connect boundary.
    Callers must enter the handle's async context and close it so owned
    resources are released on success, failure, or cancellation.
    """

    def supports(self, source: str) -> bool:
        """Return whether this resolver can attempt to resolve the source.

        Args:
            source: Untrusted source identifier, commonly a path or URI.

        Returns:
            ``True`` when the resolver recognizes the source form; this does
            not prove the source is authorized, valid, or reachable.

        Side effects:
            Implementations should not access the filesystem, network, or
            mutable external state during this classification check.
        """
        ...

    async def resolve(self, source: str) -> ResolvedSourceHandle:
        """Validate a source and return a handle with explicit resource scope.

        Args:
            source: Untrusted identifier accepted by :meth:`supports`.

        Returns:
            A handle whose content is accessed only while its async context is
            active. The handle documents whether it owns temporary artifacts
            or other resources.

        Raises:
            SourceError: For invalid, inaccessible, disallowed, or unavailable
                sources. Implementations should use typed public source errors
                rather than expose credentials or raw provider exceptions.
        """
        ...
