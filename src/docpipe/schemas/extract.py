"""POST /extract schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    text: str
    description: str
    model_id: str
    extractor: str = "langextract"
    examples: list[dict[str, Any]] = Field(default_factory=list)
    entity_classes: list[str] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    extractions: list[dict[str, Any]]
