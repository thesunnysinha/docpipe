"""Control-plane ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from docpipe.db.base import Base


class AdminUser(Base):
    """Control-plane administrator account and stored password verifier.

    ``password_hash`` stores the encoded output of the database security
    helpers, not a plaintext password. This model's active/superuser flags are
    persisted account attributes; authorization policy is enforced elsewhere.
    """

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    """Persisted control-plane event with optional tenant label and payload.

    ``payload_json`` is serialized JSON text. This row is an audit record, not
    an authorization boundary or a tenant-isolation mechanism by itself.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(64), index=True)
    tenant: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )


class IngestJob(Base):
    """Persisted summary of an ingestion run, not its document contents."""

    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(2048))
    table_name: Mapped[str] = mapped_column(String(128), index=True)
    preset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chunks_ingested: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
