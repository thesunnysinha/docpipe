"""Validation and mapping for static ``docpipe-plugin.json`` manifests."""

from __future__ import annotations

import json

from pydantic import ValidationError

from docpipe.plugins.api_version import DOCPIPE_PLUGIN_API_VERSION, PluginApiVersion
from docpipe.plugins.descriptors import (
    PluginCategory,
    PluginDescriptor,
    PluginRequirement,
)
from docpipe.plugins.errors import ManifestValidationError as ManifestValidationError
from docpipe.plugins.manifest_models import PluginManifest, PluginManifestEntry


def parse_manifest(text: str) -> dict[tuple[PluginCategory, str], PluginDescriptor]:
    """Validate manifest JSON and map entries to immutable descriptors."""
    try:
        document: object = json.loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ManifestValidationError("plugin manifest is not valid JSON") from exc

    try:
        manifest = PluginManifest.model_validate(document)
    except ValidationError as exc:
        raise ManifestValidationError("plugin manifest does not match schema") from exc

    descriptors: dict[tuple[PluginCategory, str], PluginDescriptor] = {}
    try:
        for entry in manifest.plugins:
            descriptor = _descriptor_from_entry(entry)
            key = (descriptor.category, descriptor.name)
            if key in descriptors:
                raise ManifestValidationError("plugin manifest contains duplicate plugin names")
            descriptors[key] = descriptor
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ManifestValidationError):
            raise
        raise ManifestValidationError("plugin manifest contains invalid metadata") from exc
    return descriptors


def _descriptor_from_entry(entry: PluginManifestEntry) -> PluginDescriptor:
    """Map a validated manifest entry into immutable discovery metadata."""
    api_min = PluginApiVersion.parse(entry.api_min or "1.0.0")
    api_max = PluginApiVersion.parse(entry.api_max or str(api_min))
    requirement = _requirement(entry)
    descriptor = PluginDescriptor(
        name=entry.name,
        category=entry.category,
        description=entry.description,
        stability=entry.stability,
        implementation_version=entry.implementation_version,
        requirement=requirement,
        api_min=api_min,
        api_max=api_max,
        capabilities=tuple(entry.capabilities),
        runtime_requirements=tuple(entry.runtime_requirements),
        license_id=entry.license_id,
        license_note=entry.license_note,
        deprecated=entry.deprecated,
        deprecation_message=entry.deprecation_message,
    )
    if descriptor.supports_api(DOCPIPE_PLUGIN_API_VERSION):
        return descriptor
    return PluginDescriptor(
        name=descriptor.name,
        category=descriptor.category,
        description=descriptor.description,
        stability=descriptor.stability,
        implementation_version=descriptor.implementation_version,
        requirement=descriptor.requirement,
        available=False,
        unavailable_reason="incompatible plugin API",
        api_min=descriptor.api_min,
        api_max=descriptor.api_max,
        capabilities=descriptor.capabilities,
        runtime_requirements=descriptor.runtime_requirements,
        license_id=descriptor.license_id,
        license_note=descriptor.license_note,
        deprecated=descriptor.deprecated,
        deprecation_message=descriptor.deprecation_message,
    )


def _requirement(entry: PluginManifestEntry) -> PluginRequirement | None:
    """Build optional install coordinates from a validated entry."""
    if entry.extra is None and entry.package is None:
        return None
    return PluginRequirement(extra=entry.extra, package=entry.package)
