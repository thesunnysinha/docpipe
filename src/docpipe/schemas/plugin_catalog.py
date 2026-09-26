"""Category-neutral, safe public metadata for installed plugin registrations."""

from __future__ import annotations

from pydantic import Field

from docpipe.schemas.base import ApiResponse


class CatalogPluginInfo(ApiResponse):
    """Static plugin descriptor without implementation paths or secrets."""

    name: str = Field(..., description="Registered plugin name.")
    category: str = Field(..., description="Extension point implemented by the plugin.")
    description: str = Field(..., description="Human-readable summary of the plugin.")
    stability: str = Field(..., description="Declared stability level of the plugin API.")
    implementation_version: str | None = Field(
        default=None,
        description="Version of the plugin implementation, when declared.",
    )
    api_min: str = Field(..., description="Oldest plugin API version supported.")
    api_max: str = Field(..., description="Newest plugin API version supported.")
    compatible: bool = Field(..., description="Whether the plugin supports this host API version.")
    available: bool = Field(..., description="Whether the plugin dependencies are available.")
    allowed: bool = Field(..., description="Whether policy permits loading the plugin.")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Capabilities the plugin advertises to the host.",
    )
    runtime_requirements: list[str] = Field(
        default_factory=list,
        description="Optional runtime features or dependencies required by the plugin.",
    )
    install_hint: str | None = Field(
        default=None,
        description="Package or command hint for installing the plugin, when available.",
    )
    license_id: str | None = Field(
        default=None,
        description="SPDX license identifier declared by the plugin, when available.",
    )
