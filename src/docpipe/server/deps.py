"""FastAPI dependencies for the docpipe server."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from docpipe.server.auth import require_auth

Auth = Annotated[None, Depends(require_auth)]
