"""GET /profiles and plugin resolve schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from docpipe.schemas.base import ApiRequest, ApiResponse


class ProfilesResponse(ApiResponse):
    """Install profiles, runtime presets, and server defaults."""

    install_profile: str = Field(..., description="Active install profile name.")
    install_profiles: dict[str, dict[str, Any]] = Field(
        ...,
        description="Catalog of install profiles and their dependency sets.",
    )
    runtime_presets: dict[str, dict[str, Any]] = Field(
        ...,
        description="Runtime preset defaults (parser, chunker, strategy, etc.).",
    )
    server_defaults: dict[str, Any] = Field(
        ...,
        description="Server-level default plugin and strategy selections.",
    )


class PluginResolveRequest(ApiRequest):
    """Recommend plugins for a document source and processing goal."""

    source: str | None = Field(
        default=None,
        description="File path or URL used to infer parser selection.",
        examples=["report.pdf"],
    )
    goal: Literal["ingest", "rag", "agents"] = Field(
        default="ingest",
        description="Processing goal that influences recommendations.",
    )
    preset: str | None = Field(
        default=None,
        description="Runtime preset override.",
        examples=["balanced"],
    )


class RecommendedPlugins(ApiResponse):
    """Plugin selections recommended for a source and goal."""

    parser: str = Field(..., description="Resolved parser plugin name.")
    tier: str = Field(..., description="Parser quality tier.")
    chunker: str | None = Field(default=None, description="Recommended chunker.")
    reranker: str | None = Field(default=None, description="Recommended reranker.")
    strategy: str | None = Field(default=None, description="Recommended RAG strategy.")


class PluginResolveResponse(ApiResponse):
    """Plugin resolution result."""

    source: str | None = Field(default=None, description="Input source when provided.")
    goal: str = Field(..., description="Processing goal.")
    preset: str | None = Field(default=None, description="Runtime preset applied.")
    recommended: RecommendedPlugins = Field(..., description="Resolved plugin choices.")
    preset_catalog: dict[str, str] = Field(
        ...,
        description="Map of preset name to short description.",
    )
