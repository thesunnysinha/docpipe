"""S3-compatible source handles with policy, lifecycle, and safe events."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
import re
import time
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing
from pathlib import Path
from urllib.parse import urlsplit

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.contracts.source import (
    ManagedSourceHandle,
    SourceDescriptor,
    is_valid_media_type,
)
from docpipe.plugins.errors import (
    SourceAccessError,
    SourceError,
    SourceTooLargeError,
)
from docpipe.sources.s3.schemas import S3SourceConfig
from docpipe.sources.s3.transfer import S3Client, hash_object, materialize_object, read_object
from docpipe.sources.s3.uri import parse_s3_source

_LOGGER = logging.getLogger(__name__)
_SAFE_SUFFIX = re.compile(r"\.[a-z0-9]{1,10}")


class S3SourceResolver:
    """Resolve allowed S3 objects without retaining bytes or credentials."""

    def __init__(
        self,
        config: S3SourceConfig,
        *,
        client: S3Client,
        runner: BoundedBlockingRunner,
        owns_client: bool = False,
    ) -> None:
        """Bind configuration and shared S3 transfer resources.

        The caller supplies the client and bounded blocking runner. The
        resolver closes the client during context exit only when
        ``owns_client`` is true; the runner remains caller-owned in either
        case.
        """
        self._config = config
        self._client = client
        self._runner = runner
        self._owns_client = owns_client

    def supports(self, source: str) -> bool:
        """Recognize S3 URIs without network access."""
        try:
            return urlsplit(source).scheme == "s3"
        except ValueError:
            return False

    async def __aenter__(self) -> S3SourceResolver:
        """Enter the operation-owned resolver lifecycle."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the client created by this plugin, never an injected client."""
        if self._owns_client:
            await self._runner.run(self._client.close)

    async def resolve(self, source: str) -> ManagedSourceHandle:
        """Validate policy, inspect metadata, and hash one pinned object stream."""
        bucket, key, identity = parse_s3_source(self._config, source)
        source_key = hashlib.blake2b(identity.encode(), digest_size=12).hexdigest()
        started = time.monotonic()
        _LOGGER.info(
            "source.resolve.started",
            extra={
                "event": "source.resolve.started",
                "source_scheme": "s3",
                "source_key": source_key,
            },
        )
        try:
            head = await asyncio.wait_for(
                self._runner.run(lambda: self._client.head_object(Bucket=bucket, Key=key)),
                timeout=self._config.total_timeout,
            )
            declared = head.get("ContentLength")
            if not isinstance(declared, int) or declared < 0:
                raise SourceAccessError("S3 source has invalid content length")
            if declared > self._config.max_bytes:
                raise SourceTooLargeError("S3 source exceeds configured byte limit")
            etag = head.get("ETag") if isinstance(head.get("ETag"), str) else None
            version_id = head.get("VersionId") if isinstance(head.get("VersionId"), str) else None
            size, digest = await asyncio.wait_for(
                hash_object(self._chunks(bucket, key, etag, version_id)),
                timeout=self._config.total_timeout,
            )
            if size != declared:
                raise SourceAccessError("S3 source byte count changed during resolution")
        except SourceError as error:
            self._log_failed(source_key, error.code)
            raise
        except asyncio.TimeoutError as error:
            self._log_failed(source_key, "source_timeout")
            raise SourceAccessError("S3 source deadline exceeded") from error
        except Exception as error:
            self._log_failed(source_key, "source_access_failed")
            raise SourceAccessError("S3 source could not be resolved") from error

        display_name = Path(key).name
        if not display_name or any(c in display_name for c in "/\\\x00\r\n"):
            display_name = "document"
        media_type = str(head.get("ContentType", "")).partition(";")[0].strip().casefold()
        if not is_valid_media_type(media_type):
            media_type = mimetypes.guess_type(display_name)[0] or "application/octet-stream"
        raw_version = version_id or etag
        token = hashlib.sha256(raw_version.encode()).hexdigest() if raw_version else None
        descriptor = SourceDescriptor(
            source_id=identity,
            display_name=display_name,
            media_type=media_type,
            content_length=size,
            version_token=token,
            content_fingerprint="sha256:" + digest,
        )
        artifact: Path | None = None
        artifact_lock = asyncio.Lock()

        async def stream() -> AsyncIterator[bytes]:
            try:
                chunks = self._chunks(bucket, key, etag, version_id)
                deadline = time.monotonic() + self._config.total_timeout
                async with aclosing(chunks):
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError
                        try:
                            fragment = await asyncio.wait_for(chunks.__anext__(), timeout=remaining)
                        except StopAsyncIteration:
                            break
                        yield fragment
            except SourceError:
                raise
            except asyncio.TimeoutError as error:
                raise SourceAccessError("S3 source stream deadline exceeded") from error
            except Exception as error:
                raise SourceAccessError("S3 source stream failed") from error

        async def materialize() -> Path:
            nonlocal artifact
            async with artifact_lock:
                if artifact is None:
                    suffix = Path(display_name).suffix.lower()
                    suffix = suffix if _SAFE_SUFFIX.fullmatch(suffix) else ""
                    try:
                        artifact = await asyncio.wait_for(
                            materialize_object(
                                self._chunks(bucket, key, etag, version_id),
                                root=self._config.temporary_root,
                                suffix=suffix,
                                expected_digest=digest,
                            ),
                            timeout=self._config.total_timeout,
                        )
                    except SourceError:
                        raise
                    except asyncio.TimeoutError as error:
                        raise SourceAccessError("S3 materialization deadline exceeded") from error
                    except Exception as error:
                        raise SourceAccessError("S3 materialization failed") from error
                return artifact

        async def cleanup() -> None:
            if artifact is not None:
                try:
                    await self._runner.run(lambda: artifact.unlink(missing_ok=True))
                except OSError as error:
                    _LOGGER.warning(
                        "source.cleanup.failed",
                        extra={
                            "event": "source.cleanup.failed",
                            "source_key": source_key,
                            "error_code": "source_cleanup_failed",
                        },
                    )
                    raise SourceAccessError("S3 source artifact cleanup failed") from error

        _LOGGER.info(
            "source.resolve.completed",
            extra={
                "event": "source.resolve.completed",
                "source_scheme": "s3",
                "source_key": source_key,
                "media_type": media_type,
                "byte_count": size,
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
            },
        )
        return ManagedSourceHandle(
            descriptor, stream_factory=stream, materialize_factory=materialize, cleanup=cleanup
        )

    def _chunks(
        self, bucket: str, key: str, etag: str | None, version_id: str | None
    ) -> AsyncGenerator[bytes, None]:
        return read_object(
            self._client,
            self._runner,
            bucket=bucket,
            key=key,
            etag=etag,
            version_id=version_id,
            max_bytes=self._config.max_bytes,
            chunk_bytes=self._config.chunk_bytes,
        )

    @staticmethod
    def _log_failed(source_key: str, code: str) -> None:
        _LOGGER.warning(
            "source.resolve.failed",
            extra={
                "event": "source.resolve.failed",
                "source_scheme": "s3",
                "source_key": source_key,
                "error_code": code,
            },
        )
