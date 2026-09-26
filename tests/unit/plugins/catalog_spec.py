"""Tests for isolated immutable plugin catalogs."""

from __future__ import annotations

import pytest

from docpipe.plugins.catalog import (
    PluginCatalogBuilder,
    PluginOrigin,
    PluginRegistration,
)
from docpipe.plugins.descriptors import PluginCategory, PluginDescriptor
from docpipe.plugins.errors import PluginRegistrationConflictError


def registration(
    name: str, *, origin: PluginOrigin = PluginOrigin.THIRD_PARTY
) -> PluginRegistration:
    """Build a compact vector-store registration fixture."""
    return PluginRegistration(
        category=PluginCategory.VECTORSTORE,
        name=name,
        distribution=f"docpipe-{name}",
        import_target=f"docpipe_{name}:create_plugin",
        descriptor=PluginDescriptor(
            name=name,
            category=PluginCategory.VECTORSTORE,
            description=f"{name} test plugin",
        ),
        origin=origin,
    )


def test_catalog_is_immutable_after_build() -> None:
    builder = PluginCatalogBuilder()
    builder.add(registration("qdrant"))
    catalog = builder.build()

    assert catalog.require(PluginCategory.VECTORSTORE, "qdrant").name == "qdrant"
    with pytest.raises(RuntimeError, match="already built"):
        builder.add(registration("weaviate"))


def test_catalogs_do_not_share_state_and_iterate_stably() -> None:
    first_builder = PluginCatalogBuilder()
    first_builder.add(registration("weaviate"))
    first_builder.add(registration("qdrant"))
    second_builder = PluginCatalogBuilder()
    second_builder.add(registration("milvus"))

    first = first_builder.build()
    second = second_builder.build()

    assert [item.name for item in first.registrations()] == ["qdrant", "weaviate"]
    assert [item.name for item in second.registrations()] == ["milvus"]


def test_duplicate_registration_fails_deterministically() -> None:
    builder = PluginCatalogBuilder()
    builder.add(registration("qdrant"))

    with pytest.raises(PluginRegistrationConflictError, match="qdrant"):
        builder.add(registration("qdrant"))


def test_third_party_cannot_replace_an_official_builtin() -> None:
    builder = PluginCatalogBuilder()
    builder.add(registration("pgvector", origin=PluginOrigin.BUILTIN))

    with pytest.raises(PluginRegistrationConflictError, match="official built-in"):
        builder.add(registration("pgvector"))
