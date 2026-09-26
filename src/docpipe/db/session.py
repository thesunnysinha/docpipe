"""Engine and session factory for the optional control-plane database."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from docpipe.config import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _connect_args(url: str) -> dict[str, Any]:
    """Return SQLAlchemy connection options for the configured database URL.

    SQLite connections allow use from the application's worker threads; other
    backends use SQLAlchemy's default connection arguments.
    """
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine() -> Engine | None:
    """Return the lazily initialized control-plane engine, if configured.

    The engine is cached for the process lifetime until
    :func:`shutdown_control_db` disposes it. A missing control database URL
    disables the database and returns ``None``.
    """
    global _engine
    settings = get_settings()
    url = settings.resolved_control_db_url()
    if url is None:
        return None
    if _engine is None:
        _engine = create_engine(url, connect_args=_connect_args(url), pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker[Session] | None:
    """Return the cached ORM session factory when control DB is enabled.

    Returns ``None`` when no control database URL is configured. Sessions
    created by this factory do not autoflush or autocommit; callers should use
    :func:`session_scope` for managed transaction and cleanup behavior.
    """
    global _session_factory
    engine = get_engine()
    if engine is None:
        return None
    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Yield a control-database session with commit/rollback lifecycle.

    A successful context commits once on exit. Any exception from the context
    rolls back and is re-raised; the session is closed in either case. Raises
    ``RuntimeError`` when the optional control database is disabled.
    """
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Control database is not enabled")
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_control_db() -> None:
    """Apply configured migrations and seed the initial admin if needed.

    Does nothing when the control database has no resolved URL. Migration and
    seed failures propagate to the caller; the seed operation runs inside a
    managed transaction.
    """
    settings = get_settings()
    url = settings.resolved_control_db_url()
    if url is None:
        return

    from docpipe.db.migrate import run_migrations
    from docpipe.db.seed import seed_admin_user

    run_migrations(url)
    with session_scope() as session:
        seed_admin_user(session, settings)
    logger.info("Control database ready at %s", url)


def shutdown_control_db() -> None:
    """Dispose the cached engine and clear process-level database handles."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
