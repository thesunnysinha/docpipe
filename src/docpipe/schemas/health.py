"""GET /health schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    name: str
    status: Literal["ok", "degraded", "unavailable"]
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    version: str
    plugins: dict[str, list[str]]
    dependencies: list[DependencyStatus] = Field(default_factory=list)
