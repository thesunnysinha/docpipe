"""Seed default admin user into the control-plane database."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from docpipe.config.settings import DocpipeSettings
from docpipe.db.models import AdminUser
from docpipe.db.security import hash_password


def seed_admin_user(session: Session, settings: DocpipeSettings) -> AdminUser | None:
    """Add the configured initial administrator when the table is empty.

    Returns the pending ``AdminUser`` after adding and flushing it, or ``None``
    if any admin row already exists. The caller owns the transaction and must
    commit or roll it back; the password is stored as a scrypt verifier.
    """
    existing = session.scalar(select(AdminUser).limit(1))
    if existing is not None:
        return None

    user = AdminUser(
        username=settings.resolved_admin_username(),
        password_hash=hash_password(settings.resolved_admin_password()),
        email=settings.admin_email,
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    session.flush()
    return user
