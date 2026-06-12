"""GET /profiles and plugin resolve schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProfilesResponse(BaseModel):
    install_profile: str
    install_profiles: dict[str, dict[str, Any]]
    runtime_presets: dict[str, dict[str, Any]]
    server_defaults: dict[str, Any]


class PluginResolveRequest(BaseModel):
    source: str | None = None
    goal: str = Field(default="ingest", description="ingest | rag | agents")
    preset: str | None = None


class PluginResolveResponse(BaseModel):
    source: str | None
    goal: str
    preset: str | None
    recommended: dict[str, Any]
    preset_catalog: dict[str, str]
