"""HTTP content metadata, bounds, and managed materialization."""

from __future__ import annotations

import gzip
import hashlib
import stat
from pathlib import Path

import httpx
import pytest

from docpipe.plugins.errors import SourceAccessError, SourceTooLargeError
from docpipe.testing.sources import assert_source_conformance
from tests.unit.sources.http.support import client_for, resolver_for


@pytest.mark.asyncio
async def should_materialize_private_artifact_and_clean_after_exit(tmp_path: Path) -> None:
    expected = b"report text" * 10
    async with client_for(
        lambda request: httpx.Response(
            200,
            content=expected,
            headers={"content-type": "text/plain", "content-length": str(len(expected))},
        )
    ) as client:
        handle = await resolver_for(tmp_path, client, max_bytes=1000).resolve(
            "https://example.org/report.txt?signature=private"
        )
        async with handle:
            artifact = await handle.materialize()
            assert artifact.read_bytes() == expected
            assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
            assert b"".join([part async for part in handle.open()]) == expected
        assert not artifact.exists()
        assert handle.descriptor.content_fingerprint == (
            "sha256:" + hashlib.sha256(expected).hexdigest()
        )
        assert handle.descriptor.source_id == "https://example.org/report.txt"


@pytest.mark.asyncio
async def should_not_reuse_unsafe_suffix(tmp_path: Path) -> None:
    async with client_for(lambda request: httpx.Response(200, content=b"content")) as client:
        handle = await resolver_for(tmp_path, client).resolve("https://example.org/report.!bad")
        async with handle:
            assert (await handle.materialize()).suffix == ""


@pytest.mark.asyncio
async def should_replace_unsafe_display_name(tmp_path: Path) -> None:
    async with client_for(lambda request: httpx.Response(200, content=b"content")) as client:
        handle = await resolver_for(tmp_path, client).resolve("https://example.org/report%00.txt")
        assert handle.descriptor.display_name == "document"
        await handle.aclose()
        assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def should_reject_encoded_response_before_materialization(tmp_path: Path) -> None:
    async with client_for(
        lambda request: httpx.Response(
            200,
            headers={"content-encoding": "gzip"},
            content=gzip.compress(b"encoded content"),
        )
    ) as client:
        with pytest.raises(SourceAccessError, match="content encoding"):
            await resolver_for(tmp_path, client).resolve("https://example.org/report.txt")
        assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def should_pass_public_source_contract(tmp_path: Path) -> None:
    expected = b"conformance"
    async with client_for(lambda request: httpx.Response(200, content=expected)) as client:
        await assert_source_conformance(
            resolver_for(tmp_path, client),
            source="https://example.org/doc.txt",
            expected_bytes=expected,
        )


@pytest.mark.asyncio
async def should_remove_temp_after_header_or_stream_limit(tmp_path: Path) -> None:
    for headers, body in (({"content-length": "9999"}, b""), ({}, b"x" * 20)):
        async with client_for(
            lambda request, h=headers, b=body: httpx.Response(200, headers=h, content=b)
        ) as client:
            with pytest.raises(SourceTooLargeError):
                await resolver_for(tmp_path, client, max_bytes=10).resolve(
                    "https://example.org/doc.txt"
                )
            assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("declared", ["not-a-number", "9"])
async def should_fail_closed_on_invalid_or_mismatched_length(tmp_path: Path, declared: str) -> None:
    async with client_for(
        lambda request: httpx.Response(
            200, headers={"content-length": declared}, content=b"ten-bytes!"
        )
    ) as client:
        with pytest.raises(SourceAccessError):
            await resolver_for(tmp_path, client).resolve("https://example.org/doc.txt")
        assert list(tmp_path.iterdir()) == []
