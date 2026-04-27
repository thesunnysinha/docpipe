"""HTTP Basic Auth dependency for docpipe server."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from docpipe.config import get_settings

_security = HTTPBasic(auto_error=False)


def require_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_security)],
) -> None:
    """FastAPI dependency — enforces Basic Auth when auth is enabled.

    Skipped entirely when DOCPIPE_AUTH_ENABLED=false, so the dependency
    can be used unconditionally on every endpoint.
    """
    cfg = get_settings()
    if not cfg.auth_enabled:
        return

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="docpipe"'},
        )

    ok_user = secrets.compare_digest(credentials.username.encode(), cfg.username.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), cfg.password.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="docpipe"'},
        )
