"""Reusable in-memory S3 boundary for source contract tests."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docpipe.sources.s3.configuration import S3SourceConfig


class FakeS3:
    """Deterministic S3 client that records conditional GET requests."""

    def __init__(self, content: bytes = b"document bytes") -> None:
        self.content = content
        self.get_calls: list[dict[str, object]] = []

    def head_object(self, **request: object) -> dict[str, object]:
        """Return metadata without reading the body."""
        return {
            "ContentLength": len(self.content),
            "ContentType": "text/plain",
            "ETag": '"opaque-etag"',
        }

    def get_object(self, **request: object) -> dict[str, object]:
        """Return a fresh stream, as S3 does for each GET."""
        self.get_calls.append(dict(request))
        return {"Body": BytesIO(self.content), "ContentLength": len(self.content)}

    def close(self) -> None:
        """Match the Boto3 client's lifecycle method."""
        return None


def s3_config(root: Path, *, max_bytes: int = 1024) -> S3SourceConfig:
    """Create a policy restricted to one test bucket and prefix."""
    return S3SourceConfig(
        allowed_buckets=("documents",),
        allowed_prefixes=("reports/",),
        temporary_root=root,
        max_bytes=max_bytes,
    )
