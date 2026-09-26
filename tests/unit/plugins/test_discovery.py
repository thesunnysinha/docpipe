"""Tests for static plugin metadata discovery."""

from __future__ import annotations

import importlib
from pathlib import Path

from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.discovery import discover_plugins
from tests.unit.plugins.discovery_support import distribution

FIXTURES = Path(__file__).parents[2] / "fixtures" / "plugins"


def test_discovery_uses_metadata_without_importing_plugin_modules(monkeypatch: object) -> None:
    def fail_import(name: str, package: str | None = None) -> None:
        raise AssertionError(f"discovery imported {name} from {package}")

    monkeypatch.setattr(importlib, "import_module", fail_import)  # type: ignore[attr-defined]
    result = discover_plugins([distribution("docpipe-acmevector", "acmevector", None)])

    registration = result.catalog.require(PluginCategory.VECTORSTORE, "acmevector")
    assert registration.import_target == "acmevector_plugin:create_plugin"
    assert registration.descriptor.available


def test_valid_manifest_becomes_a_rich_descriptor() -> None:
    manifest = (FIXTURES / "valid-manifest.json").read_text(encoding="utf-8")

    result = discover_plugins([distribution("docpipe-acmevector", "acmevector", manifest)])
    descriptor = result.catalog.require(PluginCategory.VECTORSTORE, "acmevector").descriptor

    assert descriptor.description == "Acme vector storage."
    assert descriptor.capabilities == ("dense-search", "metadata-filter")
    assert descriptor.license_id == "Apache-2.0"


def test_malformed_manifest_isolated_from_other_distributions() -> None:
    malformed = (FIXTURES / "invalid-manifest.json").read_text(encoding="utf-8")
    distributions = [
        distribution("broken-plugin", "broken", malformed),
        distribution("docpipe-acmevector", "acmevector", None),
    ]

    result = discover_plugins(distributions)

    assert result.catalog.get(PluginCategory.VECTORSTORE, "broken") is None
    assert result.catalog.require(PluginCategory.VECTORSTORE, "acmevector")
    assert [(issue.distribution, issue.code) for issue in result.issues] == [
        ("broken-plugin", "plugin_manifest_invalid")
    ]


def test_api_incompatible_plugin_remains_visible_but_unavailable() -> None:
    manifest = (FIXTURES / "incompatible-manifest.json").read_text(encoding="utf-8")

    result = discover_plugins([distribution("future-plugin", "future", manifest)])
    descriptor = result.catalog.require(PluginCategory.VECTORSTORE, "future").descriptor

    assert not descriptor.available
    assert descriptor.unavailable_reason == "incompatible plugin API"
    assert [(issue.distribution, issue.code) for issue in result.issues] == [
        ("future-plugin", "plugin_api_incompatible")
    ]
