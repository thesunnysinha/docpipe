"""Control-plane and HTTP authentication settings."""

from pathlib import Path

from pydantic import Field

from docpipe.config.settings_sections.base import Settings


class AdminSettings(Settings):
    """Settings for the optional control database and HTTP authentication."""

    control_db_enabled: bool = Field(
        default=False,
        description="Enable the control-plane database for users, audit events, and job history.",
    )
    control_db_url: str | None = Field(
        default=None,
        description="SQLAlchemy URL. Defaults to SQLite at control_db_path when enabled.",
    )
    control_db_path: Path = Field(
        default=Path("/data/docpipe.db"),
        description="SQLite file path when control_db_url is unset.",
    )
    control_db_auto_migrate: bool = Field(
        default=True,
        description="Apply pending control-database migrations during application startup.",
    )
    admin_panel_enabled: bool = Field(
        default=True,
        description="Expose the administrative web panel when the control database is enabled.",
    )
    persist_audit_events: bool = Field(
        default=False,
        description="Persist security and administrative audit events in the control database.",
    )
    persist_ingest_jobs: bool = Field(
        default=False,
        description="Persist ingestion job state and history in the control database.",
    )
    persist_plugin_resolutions: bool = Field(
        default=False,
        description="Persist plugin resolution decisions in the control database.",
    )
    admin_username: str | None = Field(
        default=None,
        description="Defaults to DOCPIPE_USERNAME when unset.",
    )
    admin_password: str | None = Field(
        default=None,
        description="Defaults to DOCPIPE_PASSWORD when unset.",
    )
    admin_email: str = Field(
        default="admin@localhost",
        description="Email address assigned to the seeded initial administrator.",
    )
    auth_enabled: bool = Field(
        default=True, description="Require HTTP Basic authentication for protected server routes."
    )
    username: str = Field(
        default="admin",
        description="HTTP Basic username when control-database authentication is disabled.",
    )
    password: str = Field(
        default="",
        description="HTTP Basic password outside control-database auth; configure a strong secret.",
    )

    def resolved_admin_username(self) -> str:
        """Return the seeded admin username or the HTTP Basic username fallback."""
        return self.admin_username or self.username

    def resolved_admin_password(self) -> str:
        """Return the seeded admin password or the HTTP Basic password fallback."""
        return self.admin_password or self.password

    def resolved_control_db_url(self) -> str | None:
        """Return the configured control-database URL when the feature is enabled."""
        if not self.control_db_enabled:
            return None
        if self.control_db_url:
            return self.control_db_url
        path = self.control_db_path.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.resolve()}"
