"""POST /generate schemas."""

from __future__ import annotations

from pydantic import Field

from docpipe.schemas.base import ApiRequest, ApiResponse


class GenerateRequest(ApiRequest):
    """Single-shot LLM text generation (no retrieval)."""

    prompt: str = Field(..., min_length=1, description="User prompt sent to the LLM.")
    llm_provider: str = Field(..., min_length=1, description="LLM provider registry name.")
    llm_model: str = Field(..., min_length=1, description="Model identifier.")
    api_key: str | None = Field(
        default=None,
        description="Optional per-request LLM API key.",
    )


class GenerateResponse(ApiResponse):
    """Generated completion text."""

    content: str = Field(..., description="Model completion.")
