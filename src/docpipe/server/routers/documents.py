"""Parse, extract, and combined run endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from docpipe.observability.spans import trace_operation
from docpipe.schemas import (
    ExtractRequest,
    ExtractResponse,
    ParseRequest,
    ParseResponse,
    RunRequest,
    RunResponse,
)
from docpipe.server.deps import Auth, DocumentServiceDep
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["documents"])


@router.post("/parse", response_model=ParseResponse)
@handle_docpipe_errors
async def parse_document(
    req: ParseRequest,
    _: Auth,
    service: DocumentServiceDep,
) -> ParseResponse:
    with trace_operation(
        "docpipe.parse",
        docpipe_preset=req.preset,
    ):
        return await service.parse(req)


@router.post("/extract", response_model=ExtractResponse)
@handle_docpipe_errors
async def extract_data(
    req: ExtractRequest,
    _: Auth,
    service: DocumentServiceDep,
) -> ExtractResponse:
    return await service.extract(req)


@router.post("/run", response_model=RunResponse)
@handle_docpipe_errors
async def run_pipeline(
    req: RunRequest,
    _: Auth,
    service: DocumentServiceDep,
) -> RunResponse:
    """Parse a document and run structured extraction."""
    return await service.run(req)
