"""The distributable wheel preserves built-in discovery semantics."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from docpipe.plugins.catalog import PluginOrigin
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.discovery import discover_plugins

ROOT = Path(__file__).resolve().parents[2]


def should_discover_installed_core_wheel_without_self_registration_conflicts(
    tmp_path: Path,
) -> None:
    """Build the real wheel and inspect its installed entry-point metadata."""
    target = tmp_path / "site"
    prebuilt = os.environ.get("DOCPIPE_TEST_CORE_WHEEL")
    if prebuilt:
        wheel = Path(prebuilt)
    else:
        if importlib.util.find_spec("hatchling") is None:
            pytest.skip("hatchling is required for the wheel packaging test")
        distributions = tmp_path / "dist"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "-o",
                str(distributions),
                str(ROOT),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        wheel = next(distributions.glob("*.whl"))
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
        check=True,
        capture_output=True,
        text=True,
    )

    installed = tuple(importlib.metadata.distributions(path=[str(target)]))
    result = discover_plugins(installed)

    assert result.issues == ()
    assert result.catalog.require(PluginCategory.SOURCE, "s3").origin is PluginOrigin.BUILTIN
    assert (
        result.catalog.require(PluginCategory.VECTORSTORE, "qdrant").origin is PluginOrigin.BUILTIN
    )
