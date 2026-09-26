"""Public catalog discovery is safe and independent of plugin imports."""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.plugins.api_version import PluginApiVersion
from docpipe.plugins.catalog import (
    PluginCatalogBuilder,
    PluginOrigin,
    PluginRegistration,
)
from docpipe.plugins.descriptors import (
    PluginCategory,
    PluginDescriptor,
    PluginRequirement,
    PluginStability,
    RuntimeRequirement,
)
from docpipe.registry.registry import PluginRegistry
from docpipe.server.app import create_app
from docpipe.server.services.discovery import DiscoveryService


def _catalog():
    builder = PluginCatalogBuilder()
    for name, available, compatible in (
        ("mock-vectors", True, True),
        ("unavailable-vectors", False, True),
        ("old-vectors", True, False),
    ):
        builder.add(
            PluginRegistration(
                category=PluginCategory.VECTORSTORE,
                name=name,
                distribution="acme-vectors",
                import_target="uninstalled_optional_plugin:factory",
                descriptor=PluginDescriptor(
                    name=name,
                    category=PluginCategory.VECTORSTORE,
                    description="Mock vector adapter.",
                    stability=PluginStability.EXPERIMENTAL,
                    available=available,
                    unavailable_reason=None if available else "missing dependency",
                    api_min=PluginApiVersion(0, 9, 0),
                    api_max=PluginApiVersion(1 if compatible else 0, 0 if compatible else 9, 0),
                    capabilities=("dense-search",),
                    requirement=PluginRequirement(package="acme-vectors"),
                    runtime_requirements=(RuntimeRequirement.EXTERNAL_SERVICE,),
                ),
                origin=PluginOrigin.THIRD_PARTY,
            )
        )
    return builder.build()


def test_catalog_keeps_unavailable_and_incompatible_visible_without_importing() -> None:
    settings = DocpipeSettings()
    runtime = build_runtime(settings, catalog=_catalog(), legacy_registry=PluginRegistry())

    response = DiscoveryService(settings, runtime.legacy_registry, runtime).list_plugins()

    entries = response.catalog["vectorstore"]
    assert set(entries) == {"mock-vectors", "unavailable-vectors", "old-vectors"}
    assert entries["mock-vectors"].capabilities == ["dense-search"]
    assert entries["mock-vectors"].runtime_requirements == ["external-service"]
    assert entries["mock-vectors"].install_hint == "pip install acme-vectors"
    assert entries["unavailable-vectors"].available is False
    assert entries["old-vectors"].compatible is False
    assert "uninstalled_optional_plugin" not in sys.modules
    assert "import_target" not in entries["mock-vectors"].model_dump_json()


def test_catalog_tenant_allowlist_only_changes_allowed_flag() -> None:
    settings = DocpipeSettings(
        tenant_plugin_policies='{"tenant-a":{"enabled_vectorstores":"mock-vectors"}}'
    )
    runtime = build_runtime(settings, catalog=_catalog(), legacy_registry=PluginRegistry())
    service = DiscoveryService(settings, runtime.legacy_registry, runtime)

    ordinary = service.list_plugins(tenant_id=None).catalog["vectorstore"]
    tenant = service.list_plugins(tenant_id="tenant-a").catalog["vectorstore"]

    assert ordinary["mock-vectors"].allowed is False
    assert tenant["mock-vectors"].allowed is True
    assert tenant["old-vectors"].allowed is False
    assert tenant["mock-vectors"].available is True
    assert runtime.catalog.registrations() == _catalog().registrations()


def test_plugins_api_preserves_legacy_fields_and_adds_static_catalog() -> None:
    app = create_app(DocpipeSettings(auth_enabled=False))
    with TestClient(app) as client:
        response = client.get("/plugins")

    assert response.status_code == 200
    body = response.json()
    assert "parsers" in body
    assert "extractors" in body
    assert "source" in body["catalog"]
    assert "vectorstore" in body["catalog"]
