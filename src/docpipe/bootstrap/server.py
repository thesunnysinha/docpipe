"""Server-specific runtime construction and lifespan ownership."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from docpipe.bootstrap.runtime import DocpipeRuntime, build_runtime
from docpipe.config.settings import DocpipeSettings


def create_server_runtime(settings: DocpipeSettings) -> DocpipeRuntime:
    """Build one application-scoped server runtime."""
    return build_runtime(settings)


def create_server_lifespan(
    runtime: DocpipeRuntime,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Create a FastAPI lifespan that owns exactly one runtime."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        from docpipe.db import init_control_db, shutdown_control_db
        from docpipe.observability import shutdown_observability

        app.state.docpipe_runtime = runtime
        _validate_server_security(runtime.settings)
        async with runtime:
            try:
                if runtime.settings.control_db_enabled and runtime.settings.control_db_auto_migrate:
                    init_control_db()
                yield
            finally:
                shutdown_control_db()
                shutdown_observability()

    return lifespan


def _validate_server_security(settings: DocpipeSettings) -> None:
    """Fail startup when enabled authentication has no configured secret."""
    if not settings.auth_enabled:
        return
    password = (
        settings.resolved_admin_password() if settings.control_db_enabled else settings.password
    )
    if not password:
        raise RuntimeError(
            "Authentication is enabled but no password is configured; "
            "set DOCPIPE_PASSWORD or DOCPIPE_ADMIN_PASSWORD before starting."
        )
