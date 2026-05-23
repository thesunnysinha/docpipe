"""Factory for pgvector vs optional turbovec vector stores."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docpipe.core.errors import ConfigurationError
from docpipe.vectorstores.base import VectorBackend, resolve_vector_backend
from docpipe.vectorstores.turbovec_store import (
    delete_by_source_turbovec,
    ingest_documents_turbovec,
    load_or_create_turbovec_store,
)


def _pgvector_class() -> Any:
    from langchain_postgres import PGVector

    return PGVector


def resolve_index_dir(
    *,
    request: str | Path | None = None,
    config: str | Path | None = None,
    default: str | Path = ".docpipe/indices",
) -> Path:
    raw = request or config or default
    return Path(raw).expanduser()


def create_vectorstore(
    *,
    embeddings: Any,
    table_name: str,
    connection_string: str,
    vector_backend: VectorBackend | str = "pgvector",
    turbovec_index_dir: str | Path | None = None,
    turbovec_bit_width: int = 4,
) -> Any:
    """Return a LangChain-compatible vector store for the chosen backend."""
    backend = resolve_vector_backend(config=vector_backend)
    if backend == "pgvector":
        try:
            PGVector = _pgvector_class()
        except ImportError as err:
            raise ConfigurationError(
                "vector_backend='pgvector' requires langchain-postgres. "
                "Install with: pip install 'docpipe-sdk[pgvector]'"
            ) from err
        return PGVector(
            embeddings=embeddings,
            collection_name=table_name,
            connection=connection_string,
        )

    index_dir = resolve_index_dir(config=turbovec_index_dir)
    return load_or_create_turbovec_store(
        embeddings=embeddings,
        table_name=table_name,
        index_dir=index_dir,
        bit_width=turbovec_bit_width,
    )


def ingest_documents(
    *,
    documents: list[Any],
    embeddings: Any,
    table_name: str,
    connection_string: str,
    vector_backend: VectorBackend | str = "pgvector",
    turbovec_index_dir: str | Path | None = None,
    turbovec_bit_width: int = 4,
) -> None:
    """Embed and store documents using pgvector or turbovec."""
    backend = resolve_vector_backend(config=vector_backend)
    if backend == "pgvector":
        try:
            PGVector = _pgvector_class()
        except ImportError as err:
            raise ConfigurationError(
                "vector_backend='pgvector' requires langchain-postgres. "
                "Install with: pip install 'docpipe-sdk[pgvector]'"
            ) from err
        PGVector.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=table_name,
            connection=connection_string,
        )
        return

    index_dir = resolve_index_dir(config=turbovec_index_dir)
    ingest_documents_turbovec(
        documents=documents,
        embeddings=embeddings,
        table_name=table_name,
        index_dir=index_dir,
        bit_width=turbovec_bit_width,
    )


def list_collection_sources(
    *,
    table_name: str,
    connection_string: str,
    vector_backend: VectorBackend | str = "pgvector",
    filters: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    List distinct ingested sources for a pgvector collection (LangChain PGVector schema).

    Returns (source rows, total_chunk_count). Each row:
    ``source``, ``chunk_count``, optional ``document_id``, ``document_title``.
    """
    backend = resolve_vector_backend(config=vector_backend)
    if backend != "pgvector":
        raise ConfigurationError(
            "list_collection_sources is only supported for vector_backend='pgvector'"
        )

    import psycopg2

    filter_clause = ""
    params: list[Any] = [table_name]
    if filters:
        # Simple equality filters on cmetadata keys (same as LangChain metadata filter).
        parts: list[str] = []
        for key, value in filters.items():
            parts.append("e.cmetadata->>%s = %s")
            params.extend([key, str(value)])
        if parts:
            filter_clause = " AND " + " AND ".join(parts)

    sql = f"""
        SELECT
            e.cmetadata->>'source' AS source,
            COUNT(*)::int AS chunk_count,
            MAX(e.cmetadata->>'document_id') AS document_id,
            MAX(e.cmetadata->>'document_title') AS document_title
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE c.name = %s
          AND e.cmetadata->>'source' IS NOT NULL
          {filter_clause}
        GROUP BY e.cmetadata->>'source'
        ORDER BY source
    """  # noqa: S608

    total_sql = f"""
        SELECT COUNT(*)::int
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE c.name = %s
        {filter_clause}
    """  # noqa: S608

    with psycopg2.connect(connection_string) as conn, conn.cursor() as cur:
        cur.execute(total_sql, params)
        total_row = cur.fetchone()
        total_chunks = int(total_row[0]) if total_row else 0

        cur.execute(sql, params)
        rows = cur.fetchall()

    sources: list[dict[str, Any]] = []
    for source, chunk_count, document_id, document_title in rows:
        if not source:
            continue
        sources.append(
            {
                "source": str(source),
                "chunk_count": int(chunk_count or 0),
                "document_id": document_id,
                "document_title": document_title,
            }
        )
    return sources, total_chunks


def delete_by_source(
    *,
    embeddings: Any | None,
    table_name: str,
    connection_string: str,
    vector_backend: VectorBackend | str = "pgvector",
    turbovec_index_dir: str | Path | None = None,
    source: str | None = None,
    source_contains: str | None = None,
    match_mode: str = "exact",
) -> int:
    """Delete chunks by source metadata; returns number of rows removed."""
    backend = resolve_vector_backend(config=vector_backend)
    if backend == "pgvector":
        import psycopg2

        with psycopg2.connect(connection_string) as conn, conn.cursor() as cur:
            if match_mode == "contains":
                pattern = f"%{source_contains}%"
                sql = (
                    f"DELETE FROM {table_name} "  # noqa: S608
                    "WHERE cmetadata->>'source' LIKE %s"
                )
                cur.execute(sql, [pattern])
            else:
                sql = (
                    f"DELETE FROM {table_name} "  # noqa: S608
                    "WHERE cmetadata->>'source' = %s"
                )
                cur.execute(sql, [source])
            return int(cur.rowcount)

    index_dir = resolve_index_dir(config=turbovec_index_dir)
    return delete_by_source_turbovec(
        embeddings=embeddings,
        table_name=table_name,
        index_dir=index_dir,
        source=source,
        source_contains=source_contains,
        match_mode=match_mode,
    )
