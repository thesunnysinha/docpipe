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
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine() -> Engine | None:
    global _engine
    settings = get_settings()
    url = settings.resolved_control_db_url()
    if url is None:
        return None
    if _engine is None:
        _engine = create_engine(url, connect_args=_connect_args(url), pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker[Session] | None:
    global _session_factory
    engine = get_engine()
    if engine is None:
        return None
    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
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
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
