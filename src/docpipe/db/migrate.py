"""Alembic migration runner."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def run_migrations(database_url: str) -> None:
    ini_path = _REPO_ROOT / "alembic.ini"
    if not ini_path.exists():
        logger.warning("alembic.ini not found at %s; skipping migrations", ini_path)
        return

    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied")
