"""S3 source resolution uses the published lifecycle conformance checks."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.errors import SourceAccessError, SourceTooLargeError, UnsafeSourceError
from docpipe.sources.s3.resolver import S3SourceResolver
from docpipe.testing import assert_source_conformance
from tests.unit.sources.s3.support import FakeS3, s3_config


@pytest.mark.asyncio
async def should_conform_without_eager_materialization(tmp_path: Path) -> None:
    client = FakeS3()
    resolver = S3SourceResolver(s3_config(tmp_path), client=client, runner=BoundedBlockingRunner(2))

    await assert_source_conformance(
        resolver, source="s3://documents/reports/report.txt", expected_bytes=client.content
    )

    assert all(call["IfMatch"] == '"opaque-etag"' for call in client.get_calls)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def should_reject_bucket_and_prefix_before_network(tmp_path: Path) -> None:
    client = FakeS3()
    resolver = S3SourceResolver(s3_config(tmp_path), client=client, runner=BoundedBlockingRunner(1))

    with pytest.raises(UnsafeSourceError):
        await resolver.resolve("s3://other/reports/report.txt")
    with pytest.raises(UnsafeSourceError):
        await resolver.resolve("s3://documents/private/report.txt")
    assert not client.get_calls


@pytest.mark.asyncio
async def should_reject_oversized_head_before_download(tmp_path: Path) -> None:
    client = FakeS3(b"too large")
    resolver = S3SourceResolver(
        s3_config(tmp_path, max_bytes=2), client=client, runner=BoundedBlockingRunner(1)
    )

    with pytest.raises(SourceTooLargeError):
        await resolver.resolve("s3://documents/reports/report.txt")
    assert not client.get_calls


@pytest.mark.asyncio
async def should_remove_temp_when_object_changes(tmp_path: Path) -> None:
    client = FakeS3()
    resolver = S3SourceResolver(s3_config(tmp_path), client=client, runner=BoundedBlockingRunner(1))
    handle = await resolver.resolve("s3://documents/reports/report.txt")
    client.content = b"different bytes"

    with pytest.raises(SourceAccessError):
        async with handle:
            await handle.materialize()
    assert list(tmp_path.iterdir()) == []


def should_not_claim_malformed_s3_uris(tmp_path: Path) -> None:
    resolver = S3SourceResolver(
        s3_config(tmp_path), client=FakeS3(), runner=BoundedBlockingRunner(1)
    )
    assert not resolver.supports("s3://[malformed/report.txt")


@pytest.mark.asyncio
async def should_reject_malformed_uri_without_vendor_error(tmp_path: Path) -> None:
    resolver = S3SourceResolver(
        s3_config(tmp_path), client=FakeS3(), runner=BoundedBlockingRunner(1)
    )
    with pytest.raises(UnsafeSourceError):
        await resolver.resolve("s3://[malformed/report.txt")


@pytest.mark.asyncio
async def should_redact_vendor_error_and_object_identity(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    class FailingS3(FakeS3):
        def head_object(self, **request: object) -> dict[str, object]:
            raise RuntimeError("password=private-key")

    resolver = S3SourceResolver(
        s3_config(tmp_path), client=FailingS3(), runner=BoundedBlockingRunner(1)
    )
    with caplog.at_level(logging.INFO), pytest.raises(SourceAccessError) as failure:
        await resolver.resolve("s3://documents/reports/private-key.txt")
    assert "private-key" not in caplog.text
    assert "private-key" not in str(failure.value)
