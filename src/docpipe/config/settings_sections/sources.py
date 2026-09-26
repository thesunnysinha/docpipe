"""Local and remote document-source resolution settings."""

import tempfile
from pathlib import Path

from pydantic import Field, JsonValue

from docpipe.config.settings_sections.base import Settings


class SourceSettings(Settings):
    """Resource limits and per-plugin options for source integrations."""

    # Local-path ingestion is disabled until explicit roots are granted.
    source_allowed_roots: tuple[Path, ...] = Field(
        default_factory=tuple,
        description="Filesystem roots local-source plugins may read; empty denies local access.",
    )
    source_temporary_root: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "docpipe-sources",
        description="Private temporary directory used while downloading or resolving sources.",
    )
    source_max_bytes: int = Field(
        default=100 * 1024 * 1024, ge=1, description="Maximum source payload size in bytes."
    )
    source_chunk_bytes: int = Field(
        default=1024 * 1024,
        ge=1,
        le=8 * 1024 * 1024,
        description="Maximum bytes buffered per source transfer chunk.",
    )
    source_http_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        le=600,
        description="Timeout in seconds for each outbound HTTP source request.",
    )
    source_http_max_redirects: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum redirects followed when resolving an HTTP source.",
    )
    source_http_allowed_ports: tuple[int, ...] = Field(
        default=(80, 443), description="Destination TCP ports allowed for HTTP source URLs."
    )
    source_plugin_options: dict[str, dict[str, JsonValue]] = Field(
        default_factory=dict, description="Per-plugin source configuration, keyed by plugin name."
    )
