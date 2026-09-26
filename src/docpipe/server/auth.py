"""HTTP Basic Auth verification for protected Docpipe server routes.

Credentials are checked against the configured environment values unless the
control database is enabled, in which case active database users are checked
using their stored password hashes. Disabling ``auth_enabled`` bypasses this
dependency entirely; deployments should do so only behind a trusted network or
an equivalent authentication boundary.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select

from docpipe.config import get_settings
from docpipe.config.settings import DocpipeSettings
from docpipe.db.models import AdminUser
from docpipe.db.security import verify_password
from docpipe.db.session import get_session_factory

_security = HTTPBasic(auto_error=False)


def _verify_env_credentials(
    username: str, password: str, *, settings: DocpipeSettings | None = None
) -> bool:
    cfg = settings or get_settings()
    if not cfg.password:
        return False
    ok_user = secrets.compare_digest(username.encode(), cfg.username.encode())
    ok_pass = secrets.compare_digest(password.encode(), cfg.password.encode())
    return ok_user and ok_pass


def _verify_db_credentials(
    username: str, password: str, *, settings: DocpipeSettings | None = None
) -> bool:
    factory = get_session_factory()
    if factory is None:
        return _verify_env_credentials(username, password, settings=settings)

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


def verify_credentials(
    username: str, password: str, *, settings: DocpipeSettings | None = None
) -> bool:
    """Check credentials using the active server credential source.

    When the control database is enabled and its session factory is available,
    authentication uses active database user records and stored password
    hashes. If that factory is unavailable, it falls back to the configured
    environment credentials, which are compared in constant time.

    Args:
        username: HTTP Basic Auth username supplied by the caller.
        password: Plaintext password supplied by the caller; it is compared
            against configuration or verified against a stored password hash.
        settings: Optional settings snapshot. If omitted, process settings are
            loaded through :func:`docpipe.config.get_settings`.

    Returns:
        ``True`` only when the username/password pair is valid; otherwise
        ``False``. Database/session failures are not converted to failed login
        results and may propagate to the caller.

    Side effects:
        Database-backed verification opens a database session and performs a
        read-only lookup. This function does not log credentials.
    """
    cfg = settings or get_settings()
    if cfg.control_db_enabled:
        return _verify_db_credentials(username, password, settings=cfg)
    return _verify_env_credentials(username, password, settings=cfg)


def require_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_security)],
    request: Request,
) -> None:
    """Enforce HTTP Basic Auth for a request when authentication is enabled.

    The dependency reads the immutable runtime settings attached to the app.
    If auth is disabled it returns without inspecting supplied credentials;
    otherwise a missing or invalid pair produces an HTTP 401 response and a
    Basic Auth challenge. Credential database errors are allowed to surface as
    server errors rather than being misreported as an invalid password.

    Args:
        credentials: Optional credentials parsed by FastAPI's Basic Auth
            security scheme.
        request: Current request, used to access the application runtime.

    Raises:
        HTTPException: With status 401 when credentials are missing or invalid.

    Other failures:
        Database and runtime failures are not swallowed or misreported as
        invalid credentials; shared server error handling handles them.
    """
    cfg: DocpipeSettings = request.app.state.docpipe_runtime.settings
    if not cfg.auth_enabled:
        return

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="docpipe"'},
        )

    if not verify_credentials(credentials.username, credentials.password, settings=cfg):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="docpipe"'},
        )
