"""Base classes for HTTP API Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApiRequest(BaseModel):
    """Strict request body — rejects unknown fields."""

    model_config = ConfigDict(strict=True, populate_by_name=True)


class ApiResponse(BaseModel):
    """Strict response model for OpenAPI and client codegen."""

    model_config = ConfigDict(strict=True, populate_by_name=True)
