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
    """Parse a validated source into its requested representation.

    Authentication is required. Source access and parser selection are handled
    by the service; known Docpipe and public integration errors are mapped to
    structured HTTP errors by the route decorator.
    """
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
    """Extract structured fields from validated text using the selected extractor.

    Authentication is required. The extractor may call an external model
    provider; known Docpipe and public integration errors are normalized by the
    route decorator.
    """
    return await service.extract(req)


@router.post("/run", response_model=RunResponse)
@handle_docpipe_errors
async def run_pipeline(
    req: RunRequest,
    _: Auth,
    service: DocumentServiceDep,
) -> RunResponse:
    """Parse the requested source and extract its requested structured fields.

    Authentication is required. The service may access a remote source and use
    configured parser or extractor integrations; this route returns the combined
    result and does not create an ingest job.
    """
    return await service.run(req)
