"""S3 endpoint and credential configuration reject unsafe values."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from docpipe.sources.s3.configuration import S3SourceConfig


def should_require_tls_unless_explicitly_overridden(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        S3SourceConfig(
            allowed_buckets=("documents",),
            temporary_root=tmp_path,
            endpoint_url="http://minio.example:9000",
        )

    config = S3SourceConfig(
        allowed_buckets=("documents",),
        temporary_root=tmp_path,
        endpoint_url="http://minio.example:9000",
        allow_insecure_http=True,
    )
    assert config.endpoint_url == "http://minio.example:9000"


@pytest.mark.parametrize("endpoint", ["https://user:pass@example.com", "https://example.com/path"])
def should_reject_embedded_credentials_and_paths(tmp_path: Path, endpoint: str) -> None:
    with pytest.raises(ValidationError):
        S3SourceConfig(
            allowed_buckets=("documents",), temporary_root=tmp_path, endpoint_url=endpoint
        )


def should_require_private_temporary_root(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    with pytest.raises(ValidationError, match="temporary_root"):
        S3SourceConfig(allowed_buckets=("documents",), temporary_root=shared)
