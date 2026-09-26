"""Local source root policy, hashing, and filesystem-kind checks."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import pytest

from docpipe.config.settings import DocpipeSettings
from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.errors import SourceTooLargeError, UnsafeSourceError
from docpipe.sources.local import LocalSourceConfig, LocalSourceResolver


@pytest.mark.asyncio
async def test_local_resolution_streams_content_and_records_sha256(
    tmp_path: Path, runner: BoundedBlockingRunner, caplog: pytest.LogCaptureFixture
) -> None:
    document = tmp_path / "report.pdf"
    document.write_bytes(b"large report" * 10)
    resolver = LocalSourceResolver(
        LocalSourceConfig(allowed_roots=(tmp_path,), max_bytes=1000, chunk_bytes=13),
        runner,
    )
    with caplog.at_level(logging.INFO):
        handle = await resolver.resolve(str(document))
        async with handle:
            parts = [part async for part in handle.open()]
            materialized = await handle.materialize()

    assert b"".join(parts) == document.read_bytes()
    assert all(len(part) <= 13 for part in parts)
    assert materialized == document.resolve()
    assert handle.descriptor.content_fingerprint == (
        "sha256:" + hashlib.sha256(document.read_bytes()).hexdigest()
    )
    assert handle.descriptor.media_type == "application/pdf"
    assert "large report" not in caplog.text
    assert str(document) not in caplog.text


@pytest.mark.asyncio
async def test_local_rejects_traversal_and_symlink_escape(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("private", encoding="utf-8")
    (allowed / "escape.txt").symlink_to(outside)
    resolver = LocalSourceResolver(LocalSourceConfig(allowed_roots=(allowed,)), runner)

    with pytest.raises(UnsafeSourceError):
        await resolver.resolve(str(outside))
    with pytest.raises(UnsafeSourceError):
        await resolver.resolve(str(allowed / "escape.txt"))


@pytest.mark.asyncio
async def test_local_rejects_oversize_directory_and_nonregular_file(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    document = tmp_path / "large.txt"
    document.write_bytes(b"x" * 11)
    resolver = LocalSourceResolver(
        LocalSourceConfig(allowed_roots=(tmp_path,), max_bytes=10), runner
    )
    with pytest.raises(SourceTooLargeError):
        await resolver.resolve(str(document))
    with pytest.raises(UnsafeSourceError):
        await resolver.resolve(str(tmp_path))


def test_local_support_detection_is_pure_and_config_requires_explicit_roots(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    assert DocpipeSettings(_env_file=None).source_allowed_roots == ()
    with pytest.raises(ValueError, match="allowed_roots"):
        LocalSourceConfig(allowed_roots=())
    resolver = LocalSourceResolver(LocalSourceConfig(allowed_roots=(tmp_path,)), runner)
    assert resolver.supports(str(tmp_path / "missing.txt"))
    assert resolver.supports((tmp_path / "missing.txt").as_uri())
    assert not resolver.supports("https://example.org/document.pdf")


@pytest.mark.asyncio
async def test_changed_bytes_after_resolution_fail_closed(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    document = tmp_path / "report.txt"
    document.write_bytes(b"first version")
    resolver = LocalSourceResolver(LocalSourceConfig(allowed_roots=(tmp_path,)), runner)
    handle = await resolver.resolve(str(document))
    document.write_bytes(b"different contents")

    async with handle:
        with pytest.raises(UnsafeSourceError, match="changed"):
            _ = [part async for part in handle.open()]
        with pytest.raises(UnsafeSourceError, match="changed"):
            await handle.materialize()
