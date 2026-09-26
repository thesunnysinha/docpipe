"""Filesystem validation and bounded streaming for the local source adapter."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import BinaryIO
from urllib.parse import unquote, urlparse

from docpipe.plugins.errors import (
    SourceAccessError,
    SourceTooLargeError,
    UnsafeSourceError,
    UnsupportedSourceError,
)


def canonical_local_path(source: str, roots: tuple[Path, ...]) -> Path:
    """Resolve a local URI and reject traversal or symlink escapes."""
    parsed = urlparse(source)
    if parsed.scheme == "file":
        if parsed.netloc not in ("", "localhost") or parsed.query or parsed.fragment:
            raise UnsafeSourceError("file source URI is not permitted")
        candidate = Path(unquote(parsed.path))
    elif parsed.scheme:
        raise UnsupportedSourceError("local resolver accepts file sources only")
    else:
        candidate = Path(source)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        canonical = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise SourceAccessError("local source is unavailable") from error
    if not any(canonical.is_relative_to(root) for root in roots):
        raise UnsafeSourceError("local source lies outside allowed roots")
    return canonical


def inspect_and_hash(
    source: str, roots: tuple[Path, ...], max_bytes: int, chunk_bytes: int
) -> tuple[Path, int, int, str, tuple[int, int, int, int]]:
    """Hash verified content in bounded reads without buffering the file."""
    path = canonical_local_path(source, roots)
    with open_checked(path, max_bytes) as stream:
        info = os.fstat(stream.fileno())
        digest = hashlib.sha256()
        total = 0
        while fragment := stream.read(chunk_bytes):
            total += len(fragment)
            if total > max_bytes:
                raise SourceTooLargeError("local source exceeds configured byte limit")
            digest.update(fragment)
        end_info = os.fstat(stream.fileno())
        if end_info.st_size != info.st_size or end_info.st_mtime_ns != info.st_mtime_ns:
            raise UnsafeSourceError("local source changed during fingerprinting")
        return (
            path,
            total,
            info.st_mtime_ns,
            digest.hexdigest(),
            (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size),
        )


def open_checked(
    path: Path, max_bytes: int, *, identity: tuple[int, int, int, int] | None = None
) -> BinaryIO:
    """Open without following a replacement symlink and verify file identity."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise SourceAccessError("local source cannot be opened safely") from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise UnsafeSourceError("local source must be a regular file")
        if info.st_size > max_bytes:
            raise SourceTooLargeError("local source exceeds configured byte limit")
        if (
            identity is not None
            and (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size) != identity
        ):
            raise UnsafeSourceError("local source changed after resolution")
        return os.fdopen(descriptor, "rb", closefd=True)
    except BaseException:
        os.close(descriptor)
        raise
