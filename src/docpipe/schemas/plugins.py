"""GET /plugins response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from docpipe.schemas.base import ApiResponse


class PluginInfo(ApiResponse):
    """Metadata for a single registered plugin (parser, chunker, etc.)."""

    name: str = Field(..., description="Plugin registry name.")
    class_: str = Field(
        ...,
        alias="class",
        description="Fully qualified Python class path.",
    )
    available: bool | None = Field(
        default=None,
        description="Whether optional dependencies are installed.",
    )
    license: str | None = Field(default=None, description="SPDX or project license label.")
    requires_gpu: bool = Field(default=False, description="True when GPU is recommended.")
    formats: list[str] | None = Field(
        default=None,
        description="Supported input formats (parsers only).",
    )
    tier: str | None = Field(
        default=None,
        description="Install-profile tier: core, balanced, quality, or agents.",
    )
    allowed: bool = Field(
        ...,
        description="Whether the plugin is permitted under the active install profile.",
    )


class PluginsResponse(ApiResponse):
    """Full plugin catalog grouped by capability."""

    parsers: dict[str, PluginInfo] = Field(default_factory=dict)
    extractors: dict[str, PluginInfo] = Field(default_factory=dict)
    chunkers: dict[str, PluginInfo] = Field(default_factory=dict)
    rerankers: dict[str, PluginInfo] = Field(default_factory=dict)
    evaluators: dict[str, PluginInfo] = Field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, dict[str, dict[str, Any]]]) -> PluginsResponse:
        """Build a typed response from the registry guardrails payload."""
        return cls.model_validate(payload)
