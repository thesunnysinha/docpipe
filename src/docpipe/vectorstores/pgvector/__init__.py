"""Pgvector plugin adapter and configuration."""

from docpipe.vectorstores.pgvector.adapter import PgVectorAdapter, PgVectorRepository
from docpipe.vectorstores.pgvector.configuration import PgVectorConfig
from docpipe.vectorstores.pgvector.queries import PsycopgPgVectorRepository

__all__ = [
    "PgVectorAdapter",
    "PgVectorConfig",
    "PgVectorRepository",
    "PsycopgPgVectorRepository",
]
