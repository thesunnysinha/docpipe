"""Validated, operator-owned S3 source settings."""

from __future__ import annotations

import re
import stat
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field

from docpipe.plugins.configuration import TypedPluginConfig
from docpipe.plugins.credentials import SecretReference

_BUCKET = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


class S3SourceConfig(TypedPluginConfig):
    """Bound access to selected buckets, prefixes, endpoints, and byte limits."""

    allowed_buckets: tuple[str, ...] = Field(
        ...,
        description="Bucket names this resolver may access; at least one valid name is required.",
    )
    allowed_prefixes: tuple[str, ...] = Field(
        default=(),
        description="Allowed object-key prefixes; empty allows any key in the configured buckets.",
    )
    temporary_root: Path = Field(
        ...,
        description="Existing private directory used for temporary materialized objects.",
    )
    endpoint_url: str | None = Field(
        default=None,
        description="Optional S3-compatible origin without credentials, path, query, or fragment.",
    )
    allow_insecure_http: bool = Field(
        default=False,
        description="Allow plain HTTP for endpoint_url; use only for a trusted, isolated endpoint.",
    )
    region_name: str | None = Field(
        default=None,
        description="Optional AWS region name used when creating the S3 client.",
    )
    access_key_id_ref: SecretReference | None = Field(
        default=None,
        description="Secret reference for the access key ID; configure with secret_access_key_ref.",
    )
    secret_access_key_ref: SecretReference | None = Field(
        default=None,
        description="Secret reference for the secret access key; configure with access_key_id_ref.",
    )
    session_token_ref: SecretReference | None = Field(
        default=None,
        description="Optional session-token secret reference; requires explicit key references.",
    )
    max_bytes: int = Field(
        default=100 * 1024 * 1024,
        ge=1,
        description="Maximum object size accepted from S3, in bytes.",
    )
    chunk_bytes: int = Field(
        default=1024 * 1024,
        ge=1,
        le=8 * 1024 * 1024,
        description="Maximum bytes requested per streamed S3 object chunk.",
    )
    connect_timeout: int = Field(
        default=5,
        ge=1,
        le=120,
        description="S3 client connection timeout, in seconds.",
    )
    read_timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="S3 client socket-read timeout, in seconds.",
    )
    total_timeout: float = Field(
        default=120.0,
        gt=0,
        le=3600,
        description="Overall deadline in seconds for resolution, streaming, or materialization.",
    )

    def model_post_init(self, __context: object) -> None:
        """Canonicalize the temp root and reject ambiguous remote policy."""
        if not self.allowed_buckets or any(not _BUCKET.fullmatch(b) for b in self.allowed_buckets):
            raise ValueError("allowed_buckets must contain valid bucket names")
        if any(
            not prefix or prefix.startswith("/") or any(c in prefix for c in "?#\\\x00\r\n")
            for prefix in self.allowed_prefixes
        ):
            raise ValueError("allowed_prefixes contains an invalid prefix")
        try:
            root = self.temporary_root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ValueError("temporary_root must exist") from error
        if not root.is_dir():
            raise ValueError("temporary_root must be a directory")
        if stat.S_IMODE(root.stat().st_mode) & 0o077:
            raise ValueError("temporary_root permissions must be private")
        object.__setattr__(self, "temporary_root", root)
        if self.endpoint_url is not None:
            parsed = urlsplit(self.endpoint_url)
            if (
                parsed.scheme not in ("https", "http")
                or (parsed.scheme == "http" and not self.allow_insecure_http)
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("endpoint_url must be an approved origin without credentials")
        if (self.access_key_id_ref is None) != (self.secret_access_key_ref is None):
            raise ValueError("access_key_id_ref and secret_access_key_ref must be paired")
        if self.session_token_ref is not None and self.access_key_id_ref is None:
            raise ValueError("session_token_ref requires explicit key references")
