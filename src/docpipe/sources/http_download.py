"""Deadline-bound HTTP redirects and byte-limited temporary downloads."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote, urljoin

from docpipe.plugins.contracts.source import is_valid_media_type
from docpipe.plugins.errors import (
    SourceAccessError,
    SourceTooLargeError,
    UnsafeSourceError,
)
from docpipe.sources.http_security import HttpSecurityPolicy, inspect_http_url

_SAFE_EXTENSION = re.compile(r"\.[a-z0-9]{1,10}")


async def download_source(
    client: object,
    *,
    source: str,
    temporary_root: Path,
    max_bytes: int,
    chunk_bytes: int,
    max_redirects: int,
    policy: HttpSecurityPolicy,
) -> tuple[Path, int, str, str, str | None, str]:
    """Follow only vetted redirects and hash bytes as they are written."""
    import httpx

    assert isinstance(client, httpx.AsyncClient)
    url = source
    visited: set[str] = set()
    for hop in range(max_redirects + 1):
        parsed = inspect_http_url(url, policy)
        if url in visited:
            raise UnsafeSourceError("HTTP source redirect loop")
        visited.add(url)
        async with client.stream(
            "GET",
            url,
            headers={"accept-encoding": "identity"},
            follow_redirects=False,
        ) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location or hop >= max_redirects:
                    raise UnsafeSourceError("HTTP source redirect limit exceeded")
                candidate = urljoin(url, location)
                redirected = inspect_http_url(candidate, policy)
                if parsed.scheme == "https" and redirected.scheme != "https":
                    raise UnsafeSourceError("HTTP source redirect cannot downgrade HTTPS")
                url = candidate
                continue
            if response.status_code < 200 or response.status_code >= 300:
                raise SourceAccessError("HTTP source returned an unsuccessful response")
            _require_identity_encoding(response.headers.get("content-encoding"))
            declared = _content_length(response.headers.get("content-length"), max_bytes)
            media_type = _safe_media_type(response.headers.get("content-type"))
            path = _temporary_artifact(temporary_root, parsed.path)
            completed = False
            try:
                digest = hashlib.sha256()
                total = 0
                with path.open("wb") as target:
                    async for fragment in response.aiter_bytes(chunk_size=chunk_bytes):
                        total += len(fragment)
                        if total > max_bytes:
                            raise SourceTooLargeError("HTTP source exceeds configured byte limit")
                        digest.update(fragment)
                        target.write(fragment)
                if declared is not None and declared != total:
                    raise SourceAccessError("HTTP source byte count did not match its header")
                version = response.headers.get("etag") or response.headers.get("last-modified")
                version_token = (
                    hashlib.sha256(version.encode("utf-8")).hexdigest() if version else None
                )
                display_name = _safe_display_name(parsed.path)
                completed = True
                return path, total, digest.hexdigest(), media_type, version_token, display_name
            finally:
                if not completed:
                    path.unlink(missing_ok=True)
    raise UnsafeSourceError("HTTP source redirect limit exceeded")


def _content_length(value: str | None, max_bytes: int) -> int | None:
    if value is None:
        return None
    if not value.isascii() or not value.isdecimal():
        raise SourceAccessError("HTTP source has an invalid content length")
    declared = int(value)
    if declared > max_bytes:
        raise SourceTooLargeError("HTTP source exceeds configured byte limit")
    return declared


def _require_identity_encoding(value: str | None) -> None:
    if value is not None and value.strip().casefold() != "identity":
        raise SourceAccessError("HTTP source content encoding is not supported")


def _safe_media_type(value: str | None) -> str:
    if not value:
        return "application/octet-stream"
    media_type = value.partition(";")[0].strip().casefold()
    return media_type if is_valid_media_type(media_type) else "application/octet-stream"


def _temporary_artifact(root: Path, uri_path: str) -> Path:
    extension = Path(unquote(uri_path)).suffix.lower()
    suffix = extension if _SAFE_EXTENSION.fullmatch(extension) else ""
    descriptor, name = tempfile.mkstemp(prefix="docpipe-source-", suffix=suffix, dir=root)
    os.close(descriptor)
    path = Path(name)
    path.chmod(0o600)
    return path


def _safe_display_name(uri_path: str) -> str:
    candidate = Path(unquote(uri_path)).name.strip()
    if not candidate or any(character in candidate for character in "/\\\x00\r\n"):
        return "document"
    return candidate
