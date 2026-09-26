"""Map the immutable plugin catalog to safe, policy-aware API metadata."""

from __future__ import annotations

import re

from docpipe.plugins.api_version import DOCPIPE_PLUGIN_API_VERSION
from docpipe.plugins.catalog import PluginCatalog, PluginRegistration
from docpipe.plugins.policy import PluginPolicy, evaluate_plugin_policy
from docpipe.schemas.plugin_catalog import CatalogPluginInfo

_SAFE_PACKAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def catalog_payload(
    catalog: PluginCatalog,
    *,
    process_policy: PluginPolicy,
    tenant_policy: PluginPolicy | None = None,
) -> dict[str, dict[str, CatalogPluginInfo]]:
    """Return every registration; policy only changes per-request flags."""
    result: dict[str, dict[str, CatalogPluginInfo]] = {}
    for registration in catalog.registrations():
        descriptor = registration.descriptor
        compatible = descriptor.supports_api(DOCPIPE_PLUGIN_API_VERSION)
        decision = evaluate_plugin_policy(
            registration, process=process_policy, tenant=tenant_policy
        )
        result.setdefault(registration.category.value, {})[registration.name] = CatalogPluginInfo(
            name=registration.name,
            category=registration.category.value,
            description=descriptor.description,
            stability=descriptor.stability.value,
            implementation_version=descriptor.implementation_version,
            api_min=str(descriptor.api_min),
            api_max=str(descriptor.api_max),
            compatible=compatible,
            available=descriptor.available,
            allowed=decision.allowed and compatible,
            capabilities=list(descriptor.capabilities),
            runtime_requirements=[item.value for item in descriptor.runtime_requirements],
            install_hint=_install_hint(registration),
            license_id=descriptor.license_id,
        )
    return result


def _install_hint(registration: PluginRegistration) -> str | None:
    requirement = registration.descriptor.requirement
    if requirement is None:
        return None
    if requirement.extra and _SAFE_PACKAGE.fullmatch(requirement.extra):
        return f"pip install 'docpipe-sdk[{requirement.extra}]'"
    if requirement.package and _SAFE_PACKAGE.fullmatch(requirement.package):
        return f"pip install {requirement.package}"
    return None
