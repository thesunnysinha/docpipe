"""GET /health schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from docpipe.schemas.base import ApiResponse


class DependencyStatus(ApiResponse):
    """Health of an external dependency (database, model host, etc.)."""

    name: str = Field(..., description="Dependency identifier.")
    status: Literal["ok", "degraded", "unavailable"] = Field(
        ...,
        description="Reachability and latency bucket.",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Round-trip latency in milliseconds.",
    )
    detail: str | None = Field(default=None, description="Human-readable status detail.")


class HealthResponse(ApiResponse):
    """Overall server health snapshot."""

    status: Literal["ok", "degraded", "unavailable"] = Field(
        ...,
        description="Aggregate health derived from dependencies.",
    )
    version: str = Field(..., description="Installed docpipe version.")
    profile: str | None = Field(
        default=None,
        description="Active install profile (slim, balanced, quality, agents).",
    )
    plugins: dict[str, list[str]] = Field(
        ...,
        description="Registered plugin names grouped by capability.",
    )
    dependencies: list[DependencyStatus] = Field(
        default_factory=list,
        description="Per-dependency probe results.",
    )
