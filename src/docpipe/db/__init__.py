"""Optional control-plane database (admin users, audit, job history)."""

from docpipe.db.session import get_engine, get_session_factory, init_control_db, shutdown_control_db

__all__ = [
    "get_engine",
    "get_session_factory",
    "init_control_db",
    "shutdown_control_db",
]
