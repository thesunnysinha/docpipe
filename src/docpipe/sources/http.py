"""HTTP(S) resolver with bounded materialization and explicit cleanup."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from pydantic import Field, ValidationError

from docpipe.plugins.configuration import PluginConfig, TypedPluginConfig, validation_option_path
from docpipe.plugins.contracts.source import ManagedSourceHandle, SourceDescriptor
from docpipe.plugins.errors import (
    PluginConfigurationError,
    SourceAccessError,
    SourceError,
)
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.sources.http_download import download_source
from docpipe.sources.http_logging import redact_source_http_logs
from docpipe.sources.http_security import HttpSecurityPolicy, canonical_http_source_id
from docpipe.sources.http_transport import pinned_async_transport

_LOGGER = logging.getLogger(__name__)


class _AsyncCloseable(Protocol):
    async def aclose(self) -> None:
        """Close an owned asynchronous client."""
        ...


class HttpSourceConfig(TypedPluginConfig):
    """Network deadlines, redirect limits, and owned temporary root."""

    temporary_root: Path = Field(...)
    max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    chunk_bytes: int = Field(default=1024 * 1024, ge=1, le=8 * 1024 * 1024)
    total_timeout: float = Field(default=30.0, gt=0, le=600)
    max_redirects: int = Field(default=3, ge=0, le=10)
    allow_private: bool = Field(default=False)
    allowed_ports: tuple[int, ...] = Field(default=(80, 443))

    def model_post_init(self, __context: object) -> None:
        """Require an existing private directory instead of creating broad paths."""
        try:
            root = self.temporary_root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ValueError("temporary_root must exist") from error
        if not root.is_dir():
            raise ValueError("temporary_root must be a directory")
        object.__setattr__(self, "temporary_root", root)
        HttpSecurityPolicy(self.allow_private, self.allowed_ports)


class HttpSourceResolver:
    """Resolve HTTP bytes into one restricted, lifecycle-bound artifact."""

    def __init__(
        self,
        config: HttpSourceConfig,
        *,
        client: object | None = None,
        security: HttpSecurityPolicy | None = None,
    ) -> None:
        self._config = config
        self._client = client
        self._security = security or HttpSecurityPolicy(config.allow_private, config.allowed_ports)
        self._owned_client: _AsyncCloseable | None = None

    def supports(self, source: str) -> bool:
        """Recognize HTTP schemes without DNS or network I/O."""
        return urlsplit(source).scheme in ("http", "https")

    async def __aenter__(self) -> HttpSourceResolver:
        """Start a scoped transport only when this plugin is selected."""
        if self._client is None:
            import httpx

            owned_client = httpx.AsyncClient(
                transport=pinned_async_transport(self._security),
                timeout=httpx.Timeout(self._config.total_timeout),
                trust_env=False,
                follow_redirects=False,
            )
            self._owned_client = owned_client
            self._client = owned_client
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close this resolver's network transport at its owning scope."""
        if self._owned_client is not None:
            await self._owned_client.aclose()
            self._owned_client = None
            self._client = None

    async def resolve(self, source: str) -> ManagedSourceHandle:
        """Fetch, hash, and securely materialize one HTTP source."""
        if self._client is None:
            raise RuntimeError("HTTP source resolver requires an active client lifecycle")
        started = time.monotonic()
        source_key = hashlib.blake2b(source.encode("utf-8"), digest_size=12).hexdigest()
        _LOGGER.info(
            "source.resolve.started",
            extra={
                "event": "source.resolve.started",
                "source_scheme": "http",
                "source_key": source_key,
            },
        )
        try:
            with redact_source_http_logs():
                path, size, digest, media_type, version, name = await asyncio.wait_for(
                    download_source(
                        self._client,
                        source=source,
                        temporary_root=self._config.temporary_root,
                        max_bytes=self._config.max_bytes,
                        chunk_bytes=self._config.chunk_bytes,
                        max_redirects=self._config.max_redirects,
                        policy=self._security,
                    ),
                    timeout=self._config.total_timeout,
                )
        except SourceError as error:
            _log_failed(source_key, error.code)
            raise
        except asyncio.TimeoutError as error:
            _log_failed(source_key, "source_timeout")
            raise SourceAccessError("HTTP source deadline exceeded") from error
        except Exception as error:
            _log_failed(source_key, "source_access_failed")
            raise SourceAccessError("HTTP source could not be resolved") from error

        descriptor = SourceDescriptor(
            source_id=canonical_http_source_id(source, self._security),
            display_name=name,
            media_type=media_type,
            content_length=size,
            version_token=version,
            content_fingerprint="sha256:" + digest,
        )

        async def stream() -> AsyncIterator[bytes]:
            with path.open("rb") as file:
                while fragment := await asyncio.to_thread(file.read, self._config.chunk_bytes):
                    yield fragment

        async def materialize() -> Path:
            if not path.is_file():
                raise SourceAccessError("HTTP source artifact is unavailable")
            return path

        async def cleanup() -> None:
            try:
                await asyncio.to_thread(path.unlink, missing_ok=True)
            except OSError as error:
                _LOGGER.warning(
                    "source.cleanup.failed",
                    extra={
                        "event": "source.cleanup.failed",
                        "source_key": source_key,
                        "error_code": "source_cleanup_failed",
                    },
                )
                raise SourceAccessError("HTTP source artifact cleanup failed") from error

        _LOGGER.info(
            "source.resolve.completed",
            extra={
                "event": "source.resolve.completed",
                "source_scheme": "http",
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


def _log_failed(source_key: str, code: str) -> None:
    _LOGGER.warning(
        "source.resolve.failed",
        extra={
            "event": "source.resolve.failed",
            "source_scheme": "http",
            "source_key": source_key,
            "error_code": code,
        },
    )


def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> HttpSourceResolver:
    """Validate selected HTTP options without importing optional code at discovery."""
    if config.provider != "http":
        raise PluginConfigurationError(
            "HTTP source factory received a different provider", plugin="http"
        )
    try:
        typed = HttpSourceConfig.model_validate(config.options)
    except ValidationError as error:
        raise PluginConfigurationError(
            "HTTP source configuration is invalid",
            plugin="http",
            context={"field": validation_option_path(error, category="source_plugin")},
        ) from error
    except (TypeError, ValueError) as error:
        raise PluginConfigurationError(
            "HTTP source configuration is invalid", plugin="http"
        ) from error
    return HttpSourceResolver(typed)
