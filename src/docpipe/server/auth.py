"""HTTP Basic Auth dependency for docpipe server."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select

from docpipe.config import get_settings
from docpipe.db.models import AdminUser
from docpipe.db.security import verify_password
from docpipe.db.session import get_session_factory

_security = HTTPBasic(auto_error=False)


def _verify_env_credentials(username: str, password: str) -> bool:
    cfg = get_settings()
    ok_user = secrets.compare_digest(username.encode(), cfg.username.encode())
    ok_pass = secrets.compare_digest(password.encode(), cfg.password.encode())
    return ok_user and ok_pass


def _verify_db_credentials(username: str, password: str) -> bool:
    factory = get_session_factory()
    if factory is None:
        return _verify_env_credentials(username, password)

    with factory() as session:
        user = session.scalar(
            select(AdminUser).where(
                AdminUser.username == username,
                AdminUser.is_active.is_(True),
            )
        )
        if user is None:
            return False
        return verify_password(password, user.password_hash)


def verify_credentials(username: str, password: str) -> bool:
    cfg = get_settings()
    if cfg.control_db_enabled:
        return _verify_db_credentials(username, password)
    return _verify_env_credentials(username, password)


def require_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_security)],
) -> None:
    """FastAPI dependency — enforces Basic Auth when auth is enabled."""
    cfg = get_settings()
    if not cfg.auth_enabled:
        return

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="docpipe"'},
        )

    if not verify_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="docpipe"'},
        )
