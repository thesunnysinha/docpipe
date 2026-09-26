"""Immutable plugin catalog and its single-use construction builder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias

from docpipe.plugins.descriptors import PluginCategory, PluginDescriptor
from docpipe.plugins.errors import PluginNotFoundError, PluginRegistrationConflictError

CatalogKey: TypeAlias = tuple[PluginCategory, str]


class PluginOrigin(str, Enum):
    """Trust origin of a plugin registration."""

    BUILTIN = "builtin"
    THIRD_PARTY = "third-party"


@dataclass(frozen=True, slots=True)
class PluginRegistration:
    """Static location and metadata for one lazily loaded plugin."""

    category: PluginCategory
    name: str
    distribution: str
    import_target: str
    descriptor: PluginDescriptor
    origin: PluginOrigin

    def __post_init__(self) -> None:
        """Keep selection keys consistent with public descriptor metadata."""
        if self.name != self.descriptor.name or self.category is not self.descriptor.category:
            raise ValueError("registration identity must match its plugin descriptor")
        module, separator, attribute = self.import_target.partition(":")
        if not module or separator != ":" or not attribute:
            raise ValueError("plugin import target must use 'module:attribute' syntax")
        if not self.distribution.strip():
            raise ValueError("plugin distribution must not be empty")


class PluginCatalog:
    """Read-only snapshot of known plugin registrations."""

    def __init__(self, registrations: dict[CatalogKey, PluginRegistration]) -> None:
        self._registrations = MappingProxyType(dict(registrations))

    def get(self, category: PluginCategory, name: str) -> PluginRegistration | None:
        """Return a registration, or ``None`` when it is unknown."""
        return self._registrations.get((category, name))

    def require(self, category: PluginCategory, name: str) -> PluginRegistration:
        """Return a registration or raise a stable selection error."""
        registration = self.get(category, name)
        if registration is None:
            raise PluginNotFoundError(
                f"plugin {name!r} was not found in category {category.value!r}",
                plugin=name,
                context={"category": category.value},
            )
        return registration

    def registrations(
        self, category: PluginCategory | None = None
    ) -> tuple[PluginRegistration, ...]:
        """Return registrations in deterministic category/name order."""
        registrations = (
            item
            for item in self._registrations.values()
            if category is None or item.category is category
        )
        return tuple(sorted(registrations, key=lambda item: (item.category.value, item.name)))


class PluginCatalogBuilder:
    """Single-use mutable builder for an immutable catalog snapshot."""

    def __init__(self) -> None:
        self._registrations: dict[CatalogKey, PluginRegistration] = {}
        self._built = False

    def add(self, registration: PluginRegistration) -> None:
        """Add one unique registration before the catalog is built."""
        if self._built:
            raise RuntimeError("plugin catalog builder was already built")
        key = (registration.category, registration.name)
        existing = self._registrations.get(key)
        if existing is not None:
            qualifier = " official built-in" if existing.origin is PluginOrigin.BUILTIN else ""
            raise PluginRegistrationConflictError(
                f"plugin {registration.name!r} conflicts with{qualifier} registration",
                plugin=registration.name,
                context={
                    "category": registration.category.value,
                    "existing_distribution": existing.distribution,
                    "new_distribution": registration.distribution,
                },
            )
        self._registrations[key] = registration

    def build(self) -> PluginCatalog:
        """Freeze current registrations and permanently close this builder."""
        if self._built:
            raise RuntimeError("plugin catalog builder was already built")
        self._built = True
        return PluginCatalog(self._registrations)
