"""Tests for optional control-plane database."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from docpipe.config.settings import DocpipeSettings
from docpipe.db import init_control_db, shutdown_control_db
from docpipe.db.models import AdminUser, AuditEvent, IngestJob
from docpipe.db.repository import store_audit_event, store_ingest_job
from docpipe.db.security import hash_password, verify_password
from docpipe.db.session import get_session_factory, session_scope
from docpipe.server.app import create_app
from docpipe.server.auth import verify_credentials


def test_password_hash_roundtrip() -> None:
    stored = hash_password("secret")
    assert verify_password("secret", stored)
    assert not verify_password("wrong", stored)


def test_seed_admin_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "control.db"
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_ENABLED", "true")
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCPIPE_USERNAME", "seedadmin")
    monkeypatch.setenv("DOCPIPE_PASSWORD", "seedpass")

    shutdown_control_db()
    init_control_db()

    with session_scope() as session:
        user = session.scalar(select(AdminUser).where(AdminUser.username == "seedadmin"))
        assert user is not None
        assert user.is_superuser is True
        assert verify_password("seedpass", user.password_hash)

    shutdown_control_db()


def test_persist_flags_are_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "control.db"
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_ENABLED", "true")
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCPIPE_PERSIST_AUDIT_EVENTS", "false")
    monkeypatch.setenv("DOCPIPE_PERSIST_INGEST_JOBS", "false")

    shutdown_control_db()
    init_control_db()

    store_audit_event(event="plugin_denied", tenant=None, payload={"event": "plugin_denied"})
    store_ingest_job(
        source="file:///tmp/a.pdf",
        table_name="docs",
        preset="balanced",
        parser="markitdown",
        chunks_ingested=1,
        skipped=0,
    )

    factory = get_session_factory()
    assert factory is not None
    with factory() as session:
        assert session.scalar(select(AuditEvent)) is None
        assert session.scalar(select(IngestJob)) is None

    shutdown_control_db()


def test_auth_uses_db_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "control.db"
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_ENABLED", "true")
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCPIPE_USERNAME", "dbadmin")
    monkeypatch.setenv("DOCPIPE_PASSWORD", "dbpass")

    shutdown_control_db()
    init_control_db()

    assert verify_credentials("dbadmin", "dbpass")
    assert not verify_credentials("dbadmin", "wrong")

    shutdown_control_db()


def test_admin_panel_disabled_without_control_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_ENABLED", "false")
    monkeypatch.setenv("DOCPIPE_AUTH_ENABLED", "false")
    client = TestClient(create_app())
    resp = client.get("/admin")
    assert resp.status_code == 404


def test_admin_panel_renders_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "control.db"
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_ENABLED", "true")
    monkeypatch.setenv("DOCPIPE_CONTROL_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCPIPE_AUTH_ENABLED", "false")

    shutdown_control_db()
    init_control_db()

    client = TestClient(create_app())
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "Control plane" in resp.text
    assert "DOCPIPE_PERSIST_AUDIT_EVENTS" in resp.text

    shutdown_control_db()


def test_resolved_control_db_url_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    settings = DocpipeSettings(
        control_db_enabled=True,
        control_db_path=db_path,
    )
    assert settings.resolved_control_db_url() == f"sqlite:///{db_path.resolve()}"
