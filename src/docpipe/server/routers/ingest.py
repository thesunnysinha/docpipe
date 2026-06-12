"""Ingest, delete, search, and collection source listing."""

from __future__ import annotations

import psycopg2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from docpipe.core.errors import ConfigurationError, DocpipeError
from docpipe.observability.spans import trace_operation
from docpipe.schemas import (
    IngestRequest,
    IngestResponse,
    ListSourcesRequest,
    ListSourcesResponse,
    SearchRequest,
    SearchResponse,
)
from docpipe.schemas.delete import DeleteRequest, DeleteResponse
from docpipe.server.deps import Auth, IngestServiceDep, SettingsDep
from docpipe.server.http_errors import docpipe_http_exception
from docpipe.server.router_errors import handle_docpipe_errors

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
@handle_docpipe_errors
async def ingest_document(
    req: IngestRequest,
    _: Auth,
    settings: SettingsDep,
    service: IngestServiceDep,
) -> IngestResponse:
    with trace_operation(
        "docpipe.ingest",
        docpipe_profile=settings.profile,
        docpipe_preset=req.preset,
        docpipe_table_name=req.table_name,
        docpipe_incremental=req.incremental,
    ):
        return await service.ingest(req)


@router.post("/ingest/stream", response_class=StreamingResponse)
@handle_docpipe_errors
async def ingest_stream(
    req: IngestRequest,
    _: Auth,
    settings: SettingsDep,
    service: IngestServiceDep,
) -> StreamingResponse:
    with trace_operation(
        "docpipe.ingest.stream",
        docpipe_profile=settings.profile,
        docpipe_preset=req.preset,
        docpipe_table_name=req.table_name,
    ):
        event_stream = service.stream(req)
    return StreamingResponse(event_stream, media_type="text/event-stream")


@router.delete("/ingest", response_model=DeleteResponse)
async def delete_document(
    req: DeleteRequest,
    _: Auth,
    service: IngestServiceDep,
) -> DeleteResponse:
    with trace_operation("docpipe.ingest.delete", docpipe_table_name=req.table_name):
        try:
            return service.delete(req)
        except ConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except psycopg2.errors.UndefinedTable as exc:
            raise HTTPException(
                status_code=404, detail=f"Table '{req.table_name}' not found"
            ) from exc
        except DocpipeError as exc:
            raise docpipe_http_exception(exc) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/collection/sources", response_model=ListSourcesResponse)
async def list_collection_sources(
    req: ListSourcesRequest,
    _: Auth,
    service: IngestServiceDep,
) -> ListSourcesResponse:
    with trace_operation("docpipe.collection.sources", docpipe_table_name=req.table_name):
        try:
            return service.list_sources(req)
        except ConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DocpipeError as exc:
            raise docpipe_http_exception(exc) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/search", response_model=SearchResponse)
@handle_docpipe_errors
async def search_documents(
    req: SearchRequest,
    _: Auth,
    service: IngestServiceDep,
) -> SearchResponse:
    return service.search(req)
