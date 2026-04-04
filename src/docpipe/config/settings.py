"""Pydantic Settings for docpipe configuration."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class DocpipeSettings(BaseSettings):
    """Configuration loaded from env vars, YAML, or constructor."""

    model_config = {"env_prefix": "DOCPIPE_", "env_nested_delimiter": "__"}

    # Parser settings
    default_parser: str = "docling"
    parser_options: dict[str, Any] = Field(default_factory=dict)

    # Extractor settings
    default_extractor: str = "langextract"
    extractor_options: dict[str, Any] = Field(default_factory=dict)

    # Ingestion settings
    db_connection_string: str | None = None
    db_table_name: str = "docpipe_documents"
    embedding_provider: str | None = None
    embedding_model: str | None = None
    chunk_size: int = 1000
    chunk_overlap: int = 200
    ingest_mode: str = "both"

    # Server settings
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Pipeline settings
    max_concurrency: int = 4

    # Logging
    log_level: str = "INFO"
