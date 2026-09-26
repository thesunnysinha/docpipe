"""Category-neutral, safe public metadata for installed plugin registrations."""

from __future__ import annotations

from pydantic import Field

from docpipe.schemas.base import ApiResponse


class CatalogPluginInfo(ApiResponse):
    """Static plugin descriptor without implementation paths or secrets."""

    name: str = Field(...)
    category: str = Field(...)
    description: str = Field(...)
    stability: str = Field(...)
    implementation_version: str | None = Field(default=None)
    api_min: str = Field(...)
    api_max: str = Field(...)
    compatible: bool = Field(...)
    available: bool = Field(...)
    allowed: bool = Field(...)
    capabilities: list[str] = Field(default_factory=list)
    runtime_requirements: list[str] = Field(default_factory=list)
    install_hint: str | None = Field(default=None)
    license_id: str | None = Field(default=None)
