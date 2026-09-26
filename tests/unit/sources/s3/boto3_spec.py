"""The S3 contract works with real Boto3 response and request shapes."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.sources.s3.configuration import S3SourceConfig
from docpipe.sources.s3.resolver import S3SourceResolver
from docpipe.testing import assert_source_conformance


@pytest.mark.asyncio
async def should_use_real_boto3_request_and_streaming_shapes(tmp_path: Path) -> None:
    """Stub only the service boundary, leaving SDK serialization intact."""
    boto3 = pytest.importorskip("boto3")
    from botocore.response import StreamingBody
    from botocore.stub import Stubber

    content = b"boto3 streaming response"
    client = boto3.client(
        "s3",
        endpoint_url="https://storage.example",
        aws_access_key_id="throwaway-access",
        aws_secret_access_key="throwaway-secret",
    )
    stubber = Stubber(client)
    stubber.add_response(
        "head_object",
        {"ContentLength": len(content), "ContentType": "text/plain", "ETag": '"etag"'},
        {"Bucket": "documents", "Key": "reports/report.txt"},
    )
    for _ in range(3):
        stubber.add_response(
            "get_object",
            {"Body": StreamingBody(BytesIO(content), len(content)), "ContentLength": len(content)},
            {"Bucket": "documents", "Key": "reports/report.txt", "IfMatch": '"etag"'},
        )
    with stubber:
        resolver = S3SourceResolver(
            S3SourceConfig(
                allowed_buckets=("documents",),
                allowed_prefixes=("reports/",),
                temporary_root=tmp_path,
            ),
            client=client,
            runner=BoundedBlockingRunner(2),
        )
        await assert_source_conformance(
            resolver, source="s3://documents/reports/report.txt", expected_bytes=content
        )
        stubber.assert_no_pending_responses()
    client.close()
