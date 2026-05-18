"""Minimal vector-store backend types shared by ingestion and RAG."""

from __future__ import annotations

from typing import Literal

VectorBackend = Literal["pgvector", "turbovec"]


def resolve_vector_backend(
    *,
    request: str | None = None,
    config: str | None = None,
    default: VectorBackend = "pgvector",
) -> VectorBackend:
    """Pick backend: per-request override, then config, then default."""
    raw = request or config or default
    if raw not in ("pgvector", "turbovec"):
        raise ValueError(f"vector_backend must be 'pgvector' or 'turbovec', got {raw!r}")
    return raw  # type: ignore[return-value]
