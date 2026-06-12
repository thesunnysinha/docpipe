"""Evaluation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from docpipe.schemas import EvaluateRequest, EvaluateResponse
from docpipe.server.deps import Auth, EvaluateServiceDep
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["evaluate"])


@router.post("/evaluate/run", response_model=EvaluateResponse)
@handle_docpipe_errors
async def evaluate_run(
    req: EvaluateRequest,
    _: Auth,
    service: EvaluateServiceDep,
) -> EvaluateResponse:
    return await service.run(req)
