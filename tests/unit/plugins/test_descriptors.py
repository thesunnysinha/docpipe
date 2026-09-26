"""Tests for immutable plugin descriptors and API compatibility."""

from __future__ import annotations

import pytest

from docpipe.plugins.api_version import DOCPIPE_PLUGIN_API_VERSION, PluginApiVersion
from docpipe.plugins.descriptors import (
    PluginCategory,
    PluginDescriptor,
    PluginRequirement,
    PluginStability,
    RuntimeRequirement,
)


def test_api_version_parses_and_orders_semantic_versions() -> None:
    assert PluginApiVersion.parse("1.2.3") < PluginApiVersion.parse("2.0.0")
    assert str(DOCPIPE_PLUGIN_API_VERSION) == "1.0.0"


@pytest.mark.parametrize("value", ["1", "1.2", "1.2.3.4", "v1.2.3", "1.-2.3"])
def test_api_version_rejects_non_semantic_versions(value: str) -> None:
    with pytest.raises(ValueError, match="semantic version"):
        PluginApiVersion.parse(value)


def test_descriptor_is_immutable_and_normalizes_capabilities() -> None:
    descriptor = PluginDescriptor(
        name="qdrant",
        category=PluginCategory.VECTORSTORE,
        description="Qdrant vector storage.",
        stability=PluginStability.EXPERIMENTAL,
        api_min=PluginApiVersion.parse("1.0.0"),
        api_max=PluginApiVersion.parse("1.4.0"),
        capabilities=("dense-search", "metadata-filter"),
    )

    assert descriptor.supports_api(DOCPIPE_PLUGIN_API_VERSION)
    with pytest.raises(AttributeError):
        descriptor.name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("name", ["Qdrant", "qdrant_store", "../qdrant", ""])
def test_descriptor_rejects_unstable_names(name: str) -> None:
    with pytest.raises(ValueError, match="plugin name"):
        PluginDescriptor(name=name, category=PluginCategory.VECTORSTORE, description="invalid")


def test_descriptor_rejects_duplicate_capabilities() -> None:
    with pytest.raises(ValueError, match="duplicate capabilities"):
        PluginDescriptor(
            name="qdrant",
            category=PluginCategory.VECTORSTORE,
            description="invalid",
            capabilities=("dense-search", "dense-search"),
        )


def test_descriptor_rejects_reversed_api_range() -> None:
    with pytest.raises(ValueError, match="API version range"):
        PluginDescriptor(
            name="qdrant",
            category=PluginCategory.VECTORSTORE,
            description="invalid",
            api_min=PluginApiVersion.parse("2.0.0"),
            api_max=PluginApiVersion.parse("1.0.0"),
        )


def test_descriptor_carries_install_and_runtime_requirements() -> None:
    descriptor = PluginDescriptor(
        name="qdrant",
        category=PluginCategory.VECTORSTORE,
        description="Qdrant vector storage.",
        requirement=PluginRequirement(extra="qdrant", package="qdrant-client"),
        runtime_requirements=(RuntimeRequirement.EXTERNAL_SERVICE,),
        license_id="Apache-2.0",
    )

    assert descriptor.requirement.extra == "qdrant"
    assert descriptor.runtime_requirements == (RuntimeRequirement.EXTERNAL_SERVICE,)
