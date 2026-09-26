"""Static plugin discovery that never imports implementation modules."""

from __future__ import annotations

import importlib.util
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.metadata import Distribution, distributions
from time import monotonic

from docpipe.plugins.catalog import (
    PluginCatalog,
    PluginCatalogBuilder,
    PluginOrigin,
    PluginRegistration,
)
from docpipe.plugins.descriptors import (
    PluginCategory,
    PluginDescriptor,
    PluginRequirement,
    RuntimeRequirement,
)
from docpipe.plugins.errors import PluginRegistrationConflictError
from docpipe.plugins.manifest import ManifestValidationError, parse_manifest

_LOGGER = logging.getLogger(__name__)
_ENTRY_POINT_CATEGORIES = {
    "docpipe.sources": PluginCategory.SOURCE,
    "docpipe.vectorstores": PluginCategory.VECTORSTORE,
}
_BUILTIN_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "pgvector": ("langchain_postgres", "psycopg2"),
    "turbovec": ("turbovec",),
    "qdrant": ("qdrant_client",),
    "http": ("httpx",),
    "s3": ("boto3",),
}


@dataclass(frozen=True, slots=True)
class DiscoveryIssue:
    """Safe metadata about one isolated discovery failure."""

    distribution: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Immutable discovery snapshot and non-fatal issues."""

    catalog: PluginCatalog
    issues: tuple[DiscoveryIssue, ...]


def discover_plugins(
    installed: Iterable[Distribution] | None = None,
    *,
    include_builtins: bool = True,
    logger: logging.Logger | None = None,
) -> DiscoveryResult:
    """Discover installed entry points using distribution metadata only."""
    event_logger = logger or _LOGGER
    started = monotonic()
    event_logger.info("plugin.discovery.started", extra={"event": "plugin.discovery.started"})
    builder = PluginCatalogBuilder()
    official_targets: dict[tuple[PluginCategory, str], str] = {}
    if include_builtins:
        for registration in builtin_registrations():
            builder.add(registration)
            official_targets[(registration.category, registration.name)] = (
                registration.import_target
            )

    issues: list[DiscoveryIssue] = []
    for distribution in installed if installed is not None else distributions():
        try:
            discovered_issues = _register_distribution(builder, distribution, official_targets)
        except PluginRegistrationConflictError as exc:
            event_logger.warning(
                "plugin.registration.conflict",
                extra={
                    "event": "plugin.registration.conflict",
                    "error_code": exc.code,
                },
            )
            raise
        issues.extend(discovered_issues)
        for issue in discovered_issues:
            event = (
                "plugin.manifest.invalid"
                if issue.code == "plugin_manifest_invalid"
                else "plugin.api.incompatible"
            )
            event_logger.warning(
                event,
                extra={
                    "event": event,
                    "distribution": issue.distribution,
                    "error_code": issue.code,
                },
            )

    catalog = builder.build()
    event_logger.info(
        "plugin.discovery.completed",
        extra={
            "event": "plugin.discovery.completed",
            "duration_ms": round((monotonic() - started) * 1000, 3),
            "plugin_count": len(catalog.registrations()),
            "issue_count": len(issues),
        },
    )
    return DiscoveryResult(catalog=catalog, issues=tuple(issues))


def _register_distribution(
    builder: PluginCatalogBuilder,
    distribution: Distribution,
    official_targets: Mapping[tuple[PluginCategory, str], str],
) -> tuple[DiscoveryIssue, ...]:
    try:
        distribution_name = distribution.metadata["Name"]
    except KeyError:
        distribution_name = "unknown-distribution"
    relevant = tuple(
        entry_point
        for entry_point in distribution.entry_points
        if entry_point.group in _ENTRY_POINT_CATEGORIES
        and not _is_self_registration(
            distribution_name,
            _ENTRY_POINT_CATEGORIES[entry_point.group],
            entry_point.name,
            entry_point.value,
            official_targets,
        )
    )
    if not relevant:
        return ()

    manifest_text = distribution.read_text("docpipe-plugin.json")
    descriptors: dict[tuple[PluginCategory, str], PluginDescriptor] = {}
    if manifest_text is not None:
        try:
            descriptors = parse_manifest(manifest_text)
        except ManifestValidationError:
            return (
                DiscoveryIssue(
                    distribution=distribution_name,
                    code="plugin_manifest_invalid",
                    message="plugin manifest could not be validated",
                ),
            )

    issues: list[DiscoveryIssue] = []
    for entry_point in relevant:
        category = _ENTRY_POINT_CATEGORIES[entry_point.group]
        descriptor = descriptors.get((category, entry_point.name)) or _basic_descriptor(
            category, entry_point.name, distribution_name
        )
        builder.add(
            PluginRegistration(
                category=category,
                name=entry_point.name,
                distribution=distribution_name,
                import_target=entry_point.value,
                descriptor=descriptor,
                origin=PluginOrigin.THIRD_PARTY,
            )
        )
        if not descriptor.available:
            issues.append(
                DiscoveryIssue(
                    distribution=distribution_name,
                    code="plugin_api_incompatible",
                    message="plugin does not support the current Docpipe plugin API",
                )
            )
    return tuple(issues)


def _is_self_registration(
    distribution_name: str,
    category: PluginCategory,
    name: str,
    target: str,
    official_targets: Mapping[tuple[PluginCategory, str], str],
) -> bool:
    """Ignore only this wheel's exact duplicate of an official registration."""
    normalized = distribution_name.casefold().replace("_", "-").replace(".", "-")
    return normalized == "docpipe-sdk" and official_targets.get((category, name)) == target


def _basic_descriptor(
    category: PluginCategory, name: str, distribution_name: str
) -> PluginDescriptor:
    return PluginDescriptor(
        name=name,
        category=category,
        description=f"Plugin provided by {distribution_name}.",
    )


def builtin_registrations() -> tuple[PluginRegistration, ...]:
    """Return checked-in metadata for official milestone-one plugins."""
    specifications = (
        (
            PluginCategory.VECTORSTORE,
            "pgvector",
            "docpipe.vectorstores.pgvector.factory:create_plugin",
            PluginRequirement(extra="pgvector"),
            (RuntimeRequirement.EXTERNAL_SERVICE,),
        ),
        (
            PluginCategory.VECTORSTORE,
            "turbovec",
            "docpipe.vectorstores.turbovec.factory:create_plugin",
            PluginRequirement(extra="turbovec"),
            (RuntimeRequirement.CPU,),
        ),
        (
            PluginCategory.VECTORSTORE,
            "qdrant",
            "docpipe.vectorstores.qdrant.factory:create_plugin",
            PluginRequirement(extra="qdrant"),
            (RuntimeRequirement.EXTERNAL_SERVICE,),
        ),
        (PluginCategory.SOURCE, "local", "docpipe.sources.local:create_plugin", None, ()),
        (
            PluginCategory.SOURCE,
            "http",
            "docpipe.sources.http:create_plugin",
            PluginRequirement(extra="http"),
            (),
        ),
        (
            PluginCategory.SOURCE,
            "s3",
            "docpipe.sources.s3.factory:create_plugin",
            PluginRequirement(extra="s3"),
            (RuntimeRequirement.EXTERNAL_SERVICE,),
        ),
    )
    registrations: list[PluginRegistration] = []
    for category, name, target, requirement, runtime_requirements in specifications:
        available = _builtin_dependencies_available(name)
        descriptor = PluginDescriptor(
            name=name,
            category=category,
            description=f"Official Docpipe {name} plugin.",
            requirement=requirement,
            available=available,
            unavailable_reason=None if available else "missing optional dependency",
            capabilities=("local-files", "stream", "materialize", "sha256")
            if name == "local" and category is PluginCategory.SOURCE
            else (),
            runtime_requirements=runtime_requirements,
        )
        registrations.append(
            PluginRegistration(
                category=category,
                name=name,
                distribution="docpipe-sdk",
                import_target=target,
                descriptor=descriptor,
                origin=PluginOrigin.BUILTIN,
            )
        )
    return tuple(registrations)


def _builtin_dependencies_available(name: str) -> bool:
    """Inspect top-level package specs without importing a vendor implementation."""
    for module in _BUILTIN_DEPENDENCIES.get(name, ()):
        try:
            if importlib.util.find_spec(module) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True
