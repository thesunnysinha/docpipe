"""Run the public source contract against an ephemeral S3-compatible service."""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.credentials import EnvironmentCredentialResolver
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.testing import assert_source_conformance


@pytest.mark.asyncio
async def should_conform_against_s3_service(tmp_path: Path) -> None:
    """Verify the selected S3 adapter against a disposable bucket and object."""
    endpoint = os.getenv("DOCPIPE_TEST_S3_ENDPOINT")
    access = os.getenv("DOCPIPE_TEST_S3_ACCESS_KEY")
    secret = os.getenv("DOCPIPE_TEST_S3_SECRET_KEY")
    if not (endpoint and access and secret):
        pytest.skip("S3 integration endpoint and credentials are not configured")
    boto3 = pytest.importorskip("boto3")
    from docpipe.sources.s3.factory import create_plugin

    client = boto3.client(
        "s3", endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret
    )
    for attempt in range(30):
        try:
            client.list_buckets()
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(1)
    bucket = "docpipe-test-" + uuid4().hex[:20]
    key = "reports/report.txt"
    content = b"minio contract document"
    client.create_bucket(Bucket=bucket)
    try:
        client.put_object(Bucket=bucket, Key=key, Body=content, ContentType="text/plain")
        plugin = create_plugin(
            PluginConfig(
                provider="s3",
                options={
                    "allowed_buckets": [bucket],
                    "allowed_prefixes": ["reports/"],
                    "temporary_root": str(tmp_path),
                    "endpoint_url": endpoint,
                    "allow_insecure_http": endpoint.startswith("http://"),
                    "access_key_id_ref": {"kind": "environment", "name": "S3_ACCESS"},
                    "secret_access_key_ref": {"kind": "environment", "name": "S3_SECRET"},
                },
            ),
            context=PluginFactoryContext(
                blocking_runner=BoundedBlockingRunner(2),
                credentials=EnvironmentCredentialResolver(
                    {"S3_ACCESS": access, "S3_SECRET": secret}
                ),
            ),
        )
        async with plugin:
            await assert_source_conformance(
                plugin, source=f"s3://{bucket}/{key}", expected_bytes=content
            )
    finally:
        client.delete_object(Bucket=bucket, Key=key)
        client.delete_bucket(Bucket=bucket)
        client.close()
