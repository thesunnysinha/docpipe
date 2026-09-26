"""S3 URI normalization and operator-owned bucket/prefix policy."""

from __future__ import annotations

from urllib.parse import quote, unquote, urlsplit

from docpipe.plugins.errors import UnsafeSourceError
from docpipe.sources.s3.schemas import S3SourceConfig


def parse_s3_source(config: S3SourceConfig, source: str) -> tuple[str, str, str]:
    """Return bucket, decoded key, and canonical identity after policy checks."""
    try:
        parsed = urlsplit(source)
    except ValueError as error:
        raise UnsafeSourceError("S3 source URI is malformed") from error
    bucket = parsed.netloc
    key = unquote(parsed.path.removeprefix("/"))
    if (
        parsed.scheme != "s3"
        or parsed.query
        or parsed.fragment
        or bucket not in config.allowed_buckets
        or not key
        or any(c in key for c in "\\\x00\r\n")
        or (
            config.allowed_prefixes
            and not any(key.startswith(prefix) for prefix in config.allowed_prefixes)
        )
    ):
        raise UnsafeSourceError("S3 source is outside configured bucket or prefix policy")
    return bucket, key, f"s3://{bucket}/{quote(key, safe='/')}"
