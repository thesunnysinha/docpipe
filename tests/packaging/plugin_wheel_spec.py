"""External example wheel builds and runs through public plugin contracts."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.contracts.vectorstore import CollectionRef
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.discovery import discover_plugins
from docpipe.plugins.loader import PluginFactoryContext, PluginLoader
from docpipe.plugins.policy import PluginPolicy
from docpipe.testing import assert_vector_store_conformance

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "plugin-package"


@pytest.mark.asyncio
async def test_example_wheel_static_discovery_and_conformance(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dist = tmp_path / "dist"
    target = tmp_path / "site"
    prebuilt = os.environ.get("DOCPIPE_TEST_EXAMPLE_WHEEL")
    if prebuilt:
        wheel = pathlib.Path(prebuilt)
    else:
        if importlib.util.find_spec("hatchling") is None:
            pytest.skip("hatchling is required for the wheel packaging test")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "-o",
                str(dist),
                str(EXAMPLE),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        wheel = next(dist.glob("*.whl"))
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
        check=True,
        capture_output=True,
        text=True,
    )
    distributions = tuple(importlib.metadata.distributions(path=[str(target)]))
    discovered = discover_plugins(distributions, include_builtins=False)
    registration = discovered.catalog.require(PluginCategory.VECTORSTORE, "example-memory")
    assert registration.descriptor.capabilities
    assert "example_docpipe_plugin" not in sys.modules

    monkeypatch.syspath_prepend(str(target))
    loader = PluginLoader(discovered.catalog, process_policy=PluginPolicy.create())
    loaded = loader.load(PluginCategory.VECTORSTORE, "example-memory")
    plugin = loaded.create(
        PluginConfig(provider="example-memory", options={"collection": "example"}),
        context=PluginFactoryContext(blocking_runner=BoundedBlockingRunner(1)),
    )
    await assert_vector_store_conformance(
        plugin.binding, collection=CollectionRef("example"), dimensions=3
    )
