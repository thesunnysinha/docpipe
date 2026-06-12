"""POST /cost/estimate schemas."""

from __future__ import annotations

from pydantic import Field

from docpipe.schemas.base import ApiRequest, ApiResponse


class CostEstimateRequest(ApiRequest):
    """Estimate ingest parse time and embedding cost."""

    preset: str = Field(
        default="balanced",
        pattern=r"^(fast|balanced|quality|agents)$",
        description="Runtime preset used for ingest.",
        examples=["balanced"],
    )
    page_count: int = Field(
        ...,
        ge=1,
        le=10000,
        description="Number of document pages to ingest.",
        examples=[10],
    )
    embedding_provider: str = Field(
        default="openai",
        min_length=1,
        description="Embedding provider for cost lookup.",
        examples=["openai"],
    )


class CostEstimateResponse(ApiResponse):
    """Heuristic ingest cost breakdown."""

    preset: str = Field(..., description="Resolved runtime preset.")
    page_count: int = Field(..., ge=1, description="Input page count.")
    embedding_provider: str = Field(..., description="Embedding provider used in estimate.")
    parser_tier: str | None = Field(default=None, description="Parser tier from preset.")
    chunker: str | None = Field(default=None, description="Chunker from preset.")
    estimated_parse_seconds: float = Field(..., ge=0, description="Estimated parse duration.")
    estimated_chunks: int = Field(..., ge=1, description="Approximate chunk count.")
    estimated_embedding_tokens: int = Field(..., ge=0, description="Approximate embed tokens.")
    estimated_embedding_usd: float = Field(..., ge=0, description="Embedding cost in USD.")
    estimated_total_usd: float = Field(..., ge=0, description="Total estimated USD.")
    notes: str = Field(..., description="Disclaimer about estimate accuracy.")
