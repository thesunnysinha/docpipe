"""Official conformance suite is available to third-party source authors."""

from __future__ import annotations

from pathlib import Path

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.discovery import builtin_registrations
from docpipe.plugins.errors import PluginConfigurationError
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.sources.local import LocalSourceConfig, LocalSourceResolver, create_plugin
from docpipe.testing.sources import assert_source_conformance


@pytest.mark.asyncio
async def test_public_suite_runs_against_local_plugin(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    document = tmp_path / "report.txt"
    document.write_bytes(b"public conformance bytes")
    resolver = LocalSourceResolver(LocalSourceConfig(allowed_roots=(tmp_path,)), runner)

    await assert_source_conformance(
        resolver, source=str(document), expected_bytes=document.read_bytes()
    )


def test_local_factory_rejects_unknown_options_and_static_catalog_is_actionable(
    tmp_path: Path, runner: BoundedBlockingRunner
) -> None:
    with pytest.raises(PluginConfigurationError):
        create_plugin(
            PluginConfig(provider="local", options={"allowed_roots": [str(tmp_path)], "bad": 1}),
            context=PluginFactoryContext(blocking_runner=runner),
        )
    descriptor = next(
        item.descriptor
        for item in builtin_registrations()
        if item.category is PluginCategory.SOURCE and item.name == "local"
    )
    assert "stream" in descriptor.capabilities
