"""POST /run schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    source: str
    description: str
    model_id: str
    parser: str = "docling"
    extractor: str = "langextract"
    examples: list[dict[str, Any]] = Field(default_factory=list)
    entity_classes: list[str] = Field(default_factory=list)
