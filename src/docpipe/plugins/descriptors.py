"""Immutable, side-effect-free metadata for plugin discovery."""

import re
from dataclasses import dataclass
from enum import Enum

from docpipe.plugins.api_version import DOCPIPE_PLUGIN_API_VERSION, PluginApiVersion

_STABLE_NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


class PluginCategory(str, Enum):
    """Supported plugin extension categories."""

    SOURCE = "source"
    VECTORSTORE = "vectorstore"


class PluginStability(str, Enum):
    """Published maturity of a plugin."""

    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class RuntimeRequirement(str, Enum):
    """Infrastructure a plugin needs in addition to its Python package."""

    CPU = "cpu"
    GPU = "gpu"
    EXTERNAL_SERVICE = "external-service"
    LOCAL_BINARY = "local-binary"


@dataclass(frozen=True, slots=True)
class PluginRequirement:
    """Optional installation coordinates for a plugin."""

    extra: str | None = None
    package: str | None = None

    def __post_init__(self) -> None:
        """Ensure at least one actionable installation coordinate exists."""
        if not self.extra and not self.package:
            raise ValueError("plugin requirement needs an extra or package")


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    """Immutable metadata for a plugin implementation."""

    name: str
    category: PluginCategory
    description: str
    stability: PluginStability = PluginStability.EXPERIMENTAL
    implementation_version: str | None = None
    requirement: PluginRequirement | None = None
    available: bool = True
    unavailable_reason: str | None = None
    api_min: PluginApiVersion = DOCPIPE_PLUGIN_API_VERSION
    api_max: PluginApiVersion = DOCPIPE_PLUGIN_API_VERSION
    capabilities: tuple[str, ...] = ()
    runtime_requirements: tuple[RuntimeRequirement, ...] = ()
    license_id: str | None = None
    license_note: str | None = None
    deprecated: bool = False
    deprecation_message: str | None = None

    def __post_init__(self) -> None:
        """Validate values without importing or initializing the plugin."""
        if _STABLE_NAME.fullmatch(self.name) is None:
            raise ValueError("plugin name must be lowercase kebab-case")
        if not self.description.strip():
            raise ValueError("plugin description must not be empty")
        if self.api_min > self.api_max:
            raise ValueError("invalid plugin API version range")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("duplicate capabilities are not allowed")
        invalid = [item for item in self.capabilities if _STABLE_NAME.fullmatch(item) is None]
        if invalid:
            raise ValueError(f"invalid capability names: {', '.join(invalid)}")
        if len(self.runtime_requirements) != len(set(self.runtime_requirements)):
            raise ValueError("duplicate runtime requirements are not allowed")
        if self.available and self.unavailable_reason is not None:
            raise ValueError("available plugins cannot have an unavailable reason")

    def supports_api(self, version: PluginApiVersion) -> bool:
        """Return whether the descriptor supports an API version."""
        return self.api_min <= version <= self.api_max
