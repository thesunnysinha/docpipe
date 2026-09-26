"""Bounded S3 reads and restricted artifact creation."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import aclosing
from pathlib import Path
from typing import Any, Protocol

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.errors import SourceAccessError, SourceTooLargeError


class S3Client(Protocol):
    """Small synchronous surface required from a Boto3 S3 client."""

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        """Return object metadata."""
        ...

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        """Return one streaming response body."""
        ...

    def close(self) -> None:
        """Release client transport resources."""
        ...


async def read_object(
    client: S3Client,
    runner: BoundedBlockingRunner,
    *,
    bucket: str,
    key: str,
    etag: str | None,
    version_id: str | None,
    max_bytes: int,
    chunk_bytes: int,
) -> AsyncGenerator[bytes, None]:
    """GET a pinned object and yield bounded chunks, closing the body on exit."""
    request: dict[str, str] = {"Bucket": bucket, "Key": key}
    if version_id:
        request["VersionId"] = version_id
    elif etag:
        request["IfMatch"] = etag
    response = await runner.run(lambda: client.get_object(**request))
    length = response.get("ContentLength")
    if isinstance(length, int) and length > max_bytes:
        response["Body"].close()
        raise SourceTooLargeError("S3 source exceeds configured byte limit")
    body = response["Body"]
    total = 0
    try:
        while fragment := await runner.run(body.read, chunk_bytes):
            total += len(fragment)
            if total > max_bytes:
                raise SourceTooLargeError("S3 source exceeds configured byte limit")
            yield fragment
        if isinstance(length, int) and total != length:
            raise SourceAccessError("S3 source byte count changed during transfer")
    finally:
        body.close()


async def hash_object(chunks: AsyncGenerator[bytes, None]) -> tuple[int, str]:
    """Compute a cryptographic fingerprint without buffering content."""
    digest = hashlib.sha256()
    total = 0
    async with aclosing(chunks):
        async for fragment in chunks:
            digest.update(fragment)
            total += len(fragment)
    return total, digest.hexdigest()


async def materialize_object(
    chunks: AsyncGenerator[bytes, None], *, root: Path, suffix: str, expected_digest: str
) -> Path:
    """Write a private temporary artifact and verify it matches resolved bytes."""
    descriptor, name = tempfile.mkstemp(prefix="docpipe-s3-", suffix=suffix, dir=root)
    os.close(descriptor)
    path = Path(name)
    path.chmod(0o600)
    completed = False
    try:
        digest = hashlib.sha256()
        async with aclosing(chunks):
            with path.open("wb") as target:
                async for fragment in chunks:
                    digest.update(fragment)
                    target.write(fragment)
        if digest.hexdigest() != expected_digest:
            raise SourceAccessError("S3 source changed during materialization")
        completed = True
        return path
    finally:
        if not completed:
            path.unlink(missing_ok=True)
