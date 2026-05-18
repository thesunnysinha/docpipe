"""Vector store backends (pgvector default, optional turbovec)."""

from docpipe.vectorstores.base import VectorBackend, resolve_vector_backend
from docpipe.vectorstores.factory import (
    create_vectorstore,
    delete_by_source,
    ingest_documents,
    resolve_index_dir,
)

__all__ = [
    "VectorBackend",
    "create_vectorstore",
    "delete_by_source",
    "ingest_documents",
    "resolve_index_dir",
    "resolve_vector_backend",
]
