"""Speech transcription."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from docpipe.core.errors import DocpipeError
from docpipe.observability.spans import trace_operation
from docpipe.schemas import TranscribeResponse
from docpipe.server.deps import Auth, SettingsDep, TranscribeServiceDep
from docpipe.server.http_errors import docpipe_http_exception

router = APIRouter(tags=["transcribe"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    request: Request,
    _: Auth,
    settings: SettingsDep,
    service: TranscribeServiceDep,
) -> TranscribeResponse:
    """Transcribe an authenticated multipart audio upload.

    The service validates multipart fields, writes the upload to a temporary
    file, and invokes the selected transcription backend. Invalid input maps to
    HTTP 400; Docpipe failures use the standard structured HTTP mapping.
    """
    with trace_operation(
        "docpipe.transcribe",
        docpipe_backend=settings.transcribe_default_backend,
    ):
        try:
            return await service.transcribe(request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DocpipeError as exc:
            raise docpipe_http_exception(exc) from exc
