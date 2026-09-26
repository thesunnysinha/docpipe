"""Tests for policy-gated lazy plugin loading."""

from __future__ import annotations

import importlib

import pytest

from docpipe.plugins.catalog import (
    PluginCatalogBuilder,
    PluginOrigin,
    PluginRegistration,
)
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.descriptors import (
    PluginApiVersion,
    PluginCategory,
    PluginDescriptor,
    PluginRequirement,
)
from docpipe.plugins.errors import (
    PluginDependencyError,
    PluginOperationError,
    PluginPolicyError,
)
from docpipe.plugins.loader import PluginFactoryContext, PluginLoader
from docpipe.plugins.policy import PluginPolicy


def loader_for(
    import_target: str = "qdrant_plugin:create_plugin",
    *,
    available: bool = True,
    policy: PluginPolicy | None = None,
) -> PluginLoader:
    """Build an isolated loader with one plugin registration."""
    descriptor = PluginDescriptor(
        name="qdrant",
        category=PluginCategory.VECTORSTORE,
        description="Qdrant test plugin.",
        requirement=PluginRequirement(extra="qdrant"),
        available=available,
        unavailable_reason=None if available else "incompatible plugin API",
        api_min=PluginApiVersion(1, 0, 0) if available else PluginApiVersion(2, 0, 0),
        api_max=PluginApiVersion(1, 0, 0) if available else PluginApiVersion(2, 5, 0),
    )
    builder = PluginCatalogBuilder()
    builder.add(
        PluginRegistration(
            category=descriptor.category,
            name=descriptor.name,
            distribution="docpipe-qdrant",
            import_target=import_target,
            descriptor=descriptor,
            origin=PluginOrigin.THIRD_PARTY,
        )
    )
    return PluginLoader(builder.build(), process_policy=policy or PluginPolicy.create())


def test_loader_imports_only_after_selection_and_policy_approval(monkeypatch: object) -> None:
    imports: list[str] = []

    class Module:
        @staticmethod
        def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> object:
            return {"provider": config.provider, "context": context}

    def import_module(name: str, package: str | None = None) -> object:
        imports.append(name)
        return Module()

    monkeypatch.setattr(importlib, "import_module", import_module)  # type: ignore[attr-defined]
    loader = loader_for()
    assert imports == []

    loaded = loader.load(PluginCategory.VECTORSTORE, "qdrant")

    assert imports == ["qdrant_plugin"]
    context = PluginFactoryContext(blocking_runner=object())  # type: ignore[arg-type]
    assert loaded.create(PluginConfig(provider="qdrant"), context=context) == {
        "provider": "qdrant",
        "context": context,
    }


def test_denied_or_incompatible_plugin_is_never_imported(monkeypatch: object) -> None:
    def fail_import(name: str, package: str | None = None) -> None:
        raise AssertionError(f"unexpected import: {name} from {package}")

    monkeypatch.setattr(importlib, "import_module", fail_import)  # type: ignore[attr-defined]
    denied = loader_for(policy=PluginPolicy.create(denylist={"qdrant"}))

    with pytest.raises(PluginPolicyError):
        denied.load(PluginCategory.VECTORSTORE, "qdrant")
    with pytest.raises(PluginPolicyError):
        loader_for(available=False).load(PluginCategory.VECTORSTORE, "qdrant")


def test_missing_dependency_has_declared_installation_hint(monkeypatch: object) -> None:
    def missing(name: str, package: str | None = None) -> None:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", missing)  # type: ignore[attr-defined]

    with pytest.raises(PluginDependencyError) as caught:
        loader_for().load(PluginCategory.VECTORSTORE, "qdrant")

    assert caught.value.hint == "Install docpipe-sdk[qdrant]"
    assert "ModuleNotFoundError" not in str(caught.value)


def test_factory_failure_is_translated_without_vendor_details(monkeypatch: object) -> None:
    class Module:
        @staticmethod
        def create_plugin(config: PluginConfig, *, context: PluginFactoryContext) -> object:
            raise RuntimeError("password=secret")

    monkeypatch.setattr(  # type: ignore[attr-defined]
        importlib, "import_module", lambda name: Module()
    )
    loaded = loader_for().load(PluginCategory.VECTORSTORE, "qdrant")

    with pytest.raises(PluginOperationError) as caught:
        loaded.create(
            PluginConfig(provider="qdrant"),
            context=PluginFactoryContext(blocking_runner=object()),  # type: ignore[arg-type]
        )

    assert "secret" not in str(caught.value.to_dict())
    assert isinstance(caught.value.__cause__, RuntimeError)
