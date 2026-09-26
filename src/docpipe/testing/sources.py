"""Public source-resolver conformance assertions for plugin authors."""

from __future__ import annotations

import hashlib
from pathlib import Path

from docpipe.plugins.contracts.source import SourceResolver


async def assert_source_conformance(
    resolver: SourceResolver, *, source: str, expected_bytes: bytes
) -> None:
    """Check support, streaming content, fingerprints, and handle cleanup."""
    assert resolver.supports(source), "source resolver must recognize its own source"
    handle = await resolver.resolve(source)
    assert handle.descriptor.source_id
    assert handle.descriptor.display_name
    assert handle.descriptor.content_fingerprint == (
        "sha256:" + hashlib.sha256(expected_bytes).hexdigest()
    )
    async with handle:
        fragments = [fragment async for fragment in handle.open()]
        assert b"".join(fragments) == expected_bytes
        artifact = await handle.materialize()
        assert isinstance(artifact, Path)
        assert artifact.exists()
    await handle.aclose()
    try:
        await handle.materialize()
    except RuntimeError:
        pass
    else:
        raise AssertionError("source artifact remains accessible after handle cleanup")
