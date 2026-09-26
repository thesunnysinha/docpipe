"""Installed Docpipe wheels must not collide with their built-in catalog."""

from __future__ import annotations

import pytest

from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.discovery import discover_plugins
from docpipe.plugins.errors import PluginRegistrationConflictError
from tests.unit.plugins.discovery_support import FakeDistribution, FakeEntryPoint


def should_ignore_exact_entry_points_from_the_docpipe_distribution() -> None:
    installed = FakeDistribution(
        "docpipe_sdk",
        (
            FakeEntryPoint("docpipe.sources", "local", "docpipe.sources.local:create_plugin"),
            FakeEntryPoint("docpipe.sources", "s3", "docpipe.sources.s3.factory:create_plugin"),
            FakeEntryPoint(
                "docpipe.vectorstores",
                "qdrant",
                "docpipe.vectorstores.qdrant.factory:create_plugin",
            ),
        ),
        None,
    )

    result = discover_plugins([installed])

    assert result.issues == ()
    assert result.catalog.require(PluginCategory.SOURCE, "local").origin.value == "builtin"
    assert result.catalog.require(PluginCategory.SOURCE, "s3").origin.value == "builtin"


def should_reject_a_changed_target_for_an_official_plugin_name() -> None:
    installed = FakeDistribution(
        "docpipe-sdk",
        (FakeEntryPoint("docpipe.sources", "local", "malicious:factory"),),
        None,
    )

    with pytest.raises(PluginRegistrationConflictError):
        discover_plugins([installed])
