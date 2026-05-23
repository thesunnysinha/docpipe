"""POST /generate schemas."""

from __future__ import annotations

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    prompt: str
    llm_provider: str
    llm_model: str
    api_key: str | None = None


class GenerateResponse(BaseModel):
    content: str
