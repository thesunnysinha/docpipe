"""Tests for isolated Docpipe application runtimes."""

from __future__ import annotations

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.plugins.catalog import PluginCatalogBuilder
from docpipe.plugins.lifecycle import PluginRuntime


def test_two_runtimes_do_not_share_settings_catalogs_or_registries() -> None:
    first = build_runtime(
        DocpipeSettings(server_port=8001),
        catalog=PluginCatalogBuilder().build(),
    )
    second = build_runtime(
        DocpipeSettings(server_port=8002),
        catalog=PluginCatalogBuilder().build(),
    )

    assert first is not second
    assert first.settings is not second.settings
    assert first.catalog is not second.catalog
    assert first.plugin_runtime is not second.plugin_runtime
    assert first.legacy_registry is not second.legacy_registry


@pytest.mark.asyncio
async def test_runtime_starts_and_closes_owned_resources() -> None:
    runtime = build_runtime(DocpipeSettings())

    assert not runtime.is_active
    async with runtime:
        assert runtime.is_active
        await runtime.plugin_runtime.acquire("plain", object)
    assert not runtime.is_active


def test_runtime_accepts_explicit_lifecycle_test_double() -> None:
    lifecycle = PluginRuntime()

    runtime = build_runtime(DocpipeSettings(), plugin_runtime=lifecycle)

    assert runtime.plugin_runtime is lifecycle
