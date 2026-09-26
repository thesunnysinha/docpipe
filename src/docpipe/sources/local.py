"""Local file resolver with explicit allowed-root and byte-limit policies."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import time
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, ValidationError

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig, TypedPluginConfig, validation_option_path
from docpipe.plugins.contracts.source import ManagedSourceHandle, SourceDescriptor
from docpipe.plugins.errors import PluginConfigurationError, SourceError, SourceTooLargeError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.sources.local_io import inspect_and_hash, open_checked

_LOGGER = logging.getLogger(__name__)


class LocalSourceConfig(TypedPluginConfig):
    """Restrict local sources to existing roots and bounded reads.

    Root paths are canonicalized at model construction and must already exist
    as directories. Source files are checked against those roots and their file
    identity is revalidated when opened, reducing symlink/path-swap races.
    Allowed roots are an operator trust decision: every file readable beneath
    them may be exposed to the document pipeline.

    Attributes:
        allowed_roots: Non-empty set of existing directories from which local
            documents may be read.
        max_bytes: Maximum source size accepted during inspection and streaming.
        chunk_bytes: Bounded read size used by asynchronous source streams.

    Raises:
        ValueError: If a root is missing, is not a directory, or no roots are
            configured. Pydantic validation also rejects invalid byte limits.
    """

    allowed_roots: tuple[Path, ...] = Field(
        ...,
        description="Existing directories whose files may be read as local sources; paths are canonicalized during validation.",
    )
    max_bytes: int = Field(
        default=100 * 1024 * 1024,
        ge=1,
        description="Maximum permitted size in bytes for a local source file.",
    )
    chunk_bytes: int = Field(
        default=1024 * 1024,
        ge=1,
        le=8 * 1024 * 1024,
        description="Maximum number of bytes read per filesystem operation while streaming a source.",
    )

    def model_post_init(self, __context: object) -> None:
        """Canonicalize roots once so every resolution uses the same policy."""
        if not self.allowed_roots:
            raise ValueError("allowed_roots must contain at least one directory")
        roots: list[Path] = []
        for root in self.allowed_roots:
            try:
                canonical = root.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise ValueError("allowed_roots must exist") from error
            if not canonical.is_dir():
                raise ValueError("allowed_roots must be directories")
            roots.append(canonical)
        object.__setattr__(self, "allowed_roots", tuple(dict.fromkeys(roots)))


class LocalSourceResolver:
    """Return lifecycle-bound local handles without exposing raw paths in logs."""

    def __init__(self, config: LocalSourceConfig, blocking_runner: BoundedBlockingRunner) -> None:
        """Create a resolver using validated policy and bounded file I/O.

        Args:
            config: Canonicalized allowed roots and source size/read limits.
            blocking_runner: Runtime-owned executor used for filesystem
                operations so blocking reads do not stall the event loop.
        """
        self._config = config
        self._runner = blocking_runner

    def supports(self, source: str) -> bool:
        """Check whether a value has the shape of a local path or file URI.

        This is only a scheme/shape check; it does not establish that the path
        exists or is within an allowed root. Those checks occur in
        :meth:`resolve`.
        """
        if not source or any(character in source for character in "\x00\r\n"):
            return False
        scheme = urlparse(source).scheme
        return scheme in ("", "file")

    async def resolve(self, source: str) -> ManagedSourceHandle:
        """Validate a local file and return an owned, lifecycle-bound handle.

        The resolver checks that the target is a regular file under one of the
        configured roots, enforces the maximum size, and computes a content
        fingerprint before returning. File reads and hashing run through the
        bounded blocking runner. Logs contain a stable hash derived from the
        source input rather than the raw path; this reduces accidental path
        disclosure but is not anonymization for guessable paths.

        Args:
            source: Raw filesystem path or ``file:`` URI.

        Returns:
            A one-shot handle exposing bounded streams and a lifecycle-bound
            local path. The underlying file remains caller-owned; closing the
            handle does not delete it.

        Raises:
            SourceError: If the path is invalid, outside allowed roots, cannot
                be read safely, or changes identity during validation.
            SourceTooLargeError: If the source exceeds the configured byte
                limit.

        Side effects:
            Reads the file to inspect and fingerprint its contents and emits
            structured success/failure log events. It does not modify or
            delete the source file.
        """
        started = time.monotonic()
        source_key = hashlib.blake2b(source.encode("utf-8"), digest_size=12).hexdigest()
        try:
            path, size, version, fingerprint, identity = await self._runner.run(
                lambda: inspect_and_hash(
                    source,
                    self._config.allowed_roots,
                    self._config.max_bytes,
                    self._config.chunk_bytes,
                )
            )
        except SourceError as error:
            _LOGGER.warning(
                "source.resolve.failed",
                extra={
                    "event": "source.resolve.failed",
                    "source_scheme": "file",
                    "source_key": source_key,
                    "error_code": error.code,
                },
            )
            raise
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        descriptor = SourceDescriptor(
            source_id=str(path),
            display_name=path.name,
            media_type=media_type,
            content_length=size,
            version_token=str(version),
            content_fingerprint=f"sha256:{fingerprint}",
        )

        async def stream() -> AsyncIterator[bytes]:
            """Yield bounded file fragments and close the file on all exits."""
            file = await self._runner.run(
                lambda: open_checked(path, self._config.max_bytes, identity=identity)
            )
            total = 0
            try:
                while fragment := await self._runner.run(file.read, self._config.chunk_bytes):
                    total += len(fragment)
                    if total > self._config.max_bytes:
                        raise SourceTooLargeError("local source exceeds configured byte limit")
                    yield fragment
            finally:
                file.close()

        async def materialize() -> Path:
            """Revalidate the file and return its caller-owned local path."""
            file = await self._runner.run(
                lambda: open_checked(path, self._config.max_bytes, identity=identity)
            )
            file.close()
            return path

        async def cleanup() -> None:
            """Preserve the caller-owned file; this resolver owns no file to delete."""
            # Local files remain caller-owned. The handle still has a one-shot
            # lifetime so adapters cannot reuse a path after the operation.
            return None

        _LOGGER.info(
            "source.resolve.completed",
            extra={
                "event": "source.resolve.completed",
                "source_scheme": "file",
                "source_key": source_key,
                "media_type": media_type,
                "byte_count": size,
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
            },
        )
        return ManagedSourceHandle(
            descriptor,
            stream_factory=stream,
            materialize_factory=materialize,
            cleanup=cleanup,
        )


def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> LocalSourceResolver:
    """Build a local resolver from loader-selected plugin configuration.

    Args:
        config: Provider identifier and untrusted plugin option mapping from
            the runtime configuration.
        context: Runtime factory context providing the bounded blocking runner.

    Returns:
        A resolver configured only with validated local-source options.

    Raises:
        PluginConfigurationError: If this factory receives another provider
            or local options fail validation. Error context identifies the
            invalid option path without echoing option values.
    """
    if config.provider != "local":
        raise PluginConfigurationError(
            "local source factory received a different provider", plugin="local"
        )
    try:
        typed = LocalSourceConfig.model_validate(config.options)
    except ValidationError as error:
        raise PluginConfigurationError(
            "local source configuration is invalid",
            plugin="local",
            context={"field": validation_option_path(error, category="source_plugin")},
        ) from error
    except (TypeError, ValueError) as error:
        raise PluginConfigurationError(
            "local source configuration is invalid", plugin="local"
        ) from error
    return LocalSourceResolver(typed, context.blocking_runner)
