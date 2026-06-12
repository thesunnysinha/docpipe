"""Ingest cost estimation."""

from __future__ import annotations

from fastapi import APIRouter

from docpipe.observability.spans import trace_operation
from docpipe.schemas.cost import CostEstimateRequest, CostEstimateResponse
from docpipe.server.deps import Auth, CostServiceDep
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["cost"])


@router.post("/cost/estimate", response_model=CostEstimateResponse)
@handle_docpipe_errors
async def estimate_cost(
    req: CostEstimateRequest,
    _: Auth,
    service: CostServiceDep,
) -> CostEstimateResponse:
    with trace_operation("docpipe.cost.estimate", docpipe_preset=req.preset):
        return service.estimate(req)
