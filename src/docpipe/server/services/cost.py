"""Ingest cost estimation."""

from __future__ import annotations

from docpipe.profiles.cost import estimate_ingest_cost
from docpipe.schemas.cost import CostEstimateRequest, CostEstimateResponse


class CostService:
    def estimate(self, req: CostEstimateRequest) -> CostEstimateResponse:
        data = estimate_ingest_cost(
            preset=req.preset,
            page_count=req.page_count,
            embedding_provider=req.embedding_provider,
        )
        return CostEstimateResponse(**data)
