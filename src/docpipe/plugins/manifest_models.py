"""Typed validation models for static plugin manifests."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from docpipe.plugins.descriptors import PluginCategory, PluginStability, RuntimeRequirement

_STABLE_NAME_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
_STABLE_NAME = re.compile(_STABLE_NAME_PATTERN)
_SEMANTIC_VERSION = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"


class PluginManifestEntry(BaseModel):
    """One plugin descriptor encoded in a distribution's static manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(
        ...,
        pattern=_STABLE_NAME_PATTERN,
        description="Stable lowercase kebab-case plugin name.",
    )
    category: PluginCategory = Field(..., description="Extension category provided by this plugin.")
    description: str = Field(
        ..., min_length=1, description="Short non-empty description for discovery clients."
    )
    implementation_version: str | None = Field(
        default=None, min_length=1, description="Optional version of the plugin implementation."
    )
    extra: str | None = Field(
        default=None,
        pattern=_STABLE_NAME_PATTERN,
        description="Optional Docpipe extra that installs this plugin.",
    )
    package: str | None = Field(
        default=None, min_length=1, description="Optional external package installation hint."
    )
    api_min: str | None = Field(
        default=None,
        pattern=_SEMANTIC_VERSION,
        description="Minimum Docpipe plugin API version supported, inclusive.",
    )
    api_max: str | None = Field(
        default=None,
        pattern=_SEMANTIC_VERSION,
        description="Maximum Docpipe plugin API version supported, inclusive.",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Unique stable capability identifiers implemented by the plugin.",
    )
    runtime_requirements: list[RuntimeRequirement] = Field(
        default_factory=list,
        description="Additional runtime requirements such as GPU or an external service.",
    )
    stability: PluginStability = Field(
        default=PluginStability.EXPERIMENTAL,
        description="Published maturity level of this plugin implementation.",
    )
    license_id: str | None = Field(
        default=None, min_length=1, description="Optional SPDX license identifier."
    )
    license_note: str | None = Field(
        default=None, min_length=1, description="Optional explanatory license note."
    )
    deprecated: bool = Field(
        default=False, description="Whether new integrations should avoid this plugin."
    )
    deprecation_message: str | None = Field(
        default=None,
        min_length=1,
        description="Optional migration guidance for a deprecated plugin.",
    )

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        """Require distinct stable capability identifiers."""
        if len(value) != len(set(value)) or any(
            _STABLE_NAME.fullmatch(item) is None for item in value
        ):
            raise ValueError("capabilities must be unique lowercase kebab-case names")
        return value

    @field_validator("runtime_requirements")
    @classmethod
    def validate_runtime_requirements(
        cls, value: list[RuntimeRequirement]
    ) -> list[RuntimeRequirement]:
        """Reject duplicate runtime requirement declarations."""
        if len(value) != len(set(value)):
            raise ValueError("runtime requirements must be unique")
        return value


class PluginManifest(BaseModel):
    """Top-level document accepted from ``docpipe-plugin.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = Field(
        ..., description="Version of the plugin manifest document format."
    )
    plugins: list[PluginManifestEntry] = Field(
        ..., min_length=1, description="Plugin registrations published by this distribution."
    )
