"""Blocking PostgreSQL repository for the pgvector adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast

from docpipe.plugins.contracts.vectorstore import (
    CollectionRef,
    SourceAggregate,
    VectorMatch,
    VectorQuery,
    WriteBatch,
)
from docpipe.plugins.errors import CollectionNotFoundError, PluginCapabilityError
from docpipe.vectorstores.pgvector.configuration import PgVectorConfig
from docpipe.vectorstores.pgvector.filters import compile_filter

if TYPE_CHECKING:
    from psycopg2.extensions import connection as PgConnection

_CREATE_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS docpipe_vector_collections (
    name TEXT PRIMARY KEY,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0)
);
CREATE TABLE IF NOT EXISTS docpipe_vectors (
    collection_name TEXT NOT NULL REFERENCES docpipe_vector_collections(name) ON DELETE CASCADE,
    record_id TEXT NOT NULL,
    source_id TEXT,
    document TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR NOT NULL,
    PRIMARY KEY (collection_name, record_id)
);
CREATE INDEX IF NOT EXISTS docpipe_vectors_source_idx
    ON docpipe_vectors (collection_name, source_id);
"""


class PsycopgPgVectorRepository:
    """Transactional pgvector persistence with parameterized public inputs."""

    def __init__(self, config: PgVectorConfig) -> None:
        self._config = config

    def _connect(self) -> PgConnection:
        """Open a DB-API connection without retaining credentials in state copies."""
        import psycopg2

        try:
            return cast(
                "PgConnection",
                psycopg2.connect(
                    self._config.dsn.get_secret_value(),
                    connect_timeout=max(1, round(self._config.connect_timeout_seconds)),
                ),
            )
        except psycopg2.OperationalError as exc:
            raise ConnectionError("pgvector database is unavailable") from exc

    def ensure_collection(self, collection: CollectionRef, dimensions: int) -> None:
        """Create storage schema and a dimension-checked logical collection."""
        if dimensions < 1:
            raise ValueError("collection dimensions must be positive")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(_CREATE_SCHEMA)
            cursor.execute(
                "SELECT dimensions FROM docpipe_vector_collections WHERE name = %s",
                (collection.name,),
            )
            row = cursor.fetchone()
            if row is not None and int(row[0]) != dimensions:
                raise ValueError("collection already exists with different dimensions")
            cursor.execute(
                """
                INSERT INTO docpipe_vector_collections (name, dimensions)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
                """,
                (collection.name, dimensions),
            )

    def delete_collection(self, collection: CollectionRef) -> None:
        """Delete a logical collection using its bound name."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM docpipe_vector_collections WHERE name = %s",
                (collection.name,),
            )

    def upsert(self, batch: WriteBatch) -> int:
        """Upsert all records in one transaction and return accepted count."""
        self._require_collection(batch.collection)
        statement = """
            INSERT INTO docpipe_vectors
                (collection_name, record_id, source_id, document, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::vector)
            ON CONFLICT (collection_name, record_id) DO UPDATE SET
                source_id = EXCLUDED.source_id,
                document = EXCLUDED.document,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding
        """
        with self._connect() as connection, connection.cursor() as cursor:
            for record in batch.records:
                cursor.execute(
                    statement,
                    (
                        batch.collection.name,
                        record.record_id,
                        record.source_id,
                        record.text,
                        json.dumps(_plain_json(record.metadata)),
                        _vector_literal(record.vector),
                    ),
                )
        return len(batch.records)

    def search(self, query: VectorQuery) -> tuple[VectorMatch, ...]:
        """Run dense cosine-distance search with a compiled typed filter."""
        if query.dense_vector is None:
            raise PluginCapabilityError(
                "pgvector adapter requires a dense query vector",
                plugin="pgvector",
            )
        self._require_collection(query.collection)
        compiled = compile_filter(query.filter)
        vector = _vector_literal(query.dense_vector)
        statement = f"""
            SELECT record_id, 1 - (embedding <=> %s::vector) AS score,
                   document, metadata, source_id
            FROM docpipe_vectors
            WHERE collection_name = %s AND {compiled.sql}
            ORDER BY embedding <=> %s::vector, record_id
            LIMIT %s
        """  # noqa: S608 -- compiled.sql is emitted only by the typed compiler.
        parameters = (vector, query.collection.name, *compiled.parameters, vector, query.limit)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(statement, parameters)
            rows = cursor.fetchall()
        return tuple(
            VectorMatch(
                record_id=str(row[0]),
                score=float(row[1]),
                text=str(row[2]),
                metadata=row[3] if isinstance(row[3], Mapping) else {},
                source_id=str(row[4]) if row[4] is not None else None,
            )
            for row in rows
        )

    def delete_by_source(self, collection: CollectionRef, source_id: str) -> int:
        """Delete only exact normalized source identifiers."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM docpipe_vectors WHERE collection_name = %s AND source_id = %s",
                (collection.name, source_id),
            )
            return int(cursor.rowcount)

    def aggregate_sources(self, collection: CollectionRef) -> tuple[SourceAggregate, ...]:
        """Return deterministic record counts grouped by non-null source."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source_id, COUNT(*)
                FROM docpipe_vectors
                WHERE collection_name = %s AND source_id IS NOT NULL
                GROUP BY source_id ORDER BY source_id
                """,
                (collection.name,),
            )
            rows = cursor.fetchall()
        return tuple(SourceAggregate(str(row[0]), int(row[1])) for row in rows)

    def health(self) -> bool:
        """Run a bounded no-data connectivity query."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        return row is not None and row[0] == 1

    def _require_collection(self, collection: CollectionRef) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM docpipe_vector_collections WHERE name = %s",
                (collection.name,),
            )
            if cursor.fetchone() is None:
                raise CollectionNotFoundError(
                    "vector collection was not found",
                    context={"collection": collection.name},
                )


def _vector_literal(vector: Sequence[object]) -> str:
    return "[" + ",".join(format(_numeric_value(value), ".17g") for value in vector) + "]"


def _numeric_value(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("vector values must be numeric")
    return float(value)


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value
