"""Secret-free cache identity helpers for RAG behavior."""

from __future__ import annotations

import hashlib
import json
from urllib.parse import urlsplit

from docpipe.core.types import RAGConfig

_BEHAVIOR_FIELDS = (
    "table_name",
    "embedding_provider",
    "embedding_model",
    "llm_provider",
    "llm_model",
    "strategy",
    "top_k",
    "max_chunks_per_source",
    "hyde_prompt",
    "multi_query_prompt",
    "auto_strategy_prompt",
    "multi_query_count",
    "parent_window_size",
    "hybrid_bm25_weight",
    "reranker",
    "reranker_model",
    "rerank_top_n",
    "system_prompt",
    "history",
    "response_format",
    "filters",
    "vector_backend",
    "turbovec_bit_width",
)


def cache_namespace(config: RAGConfig) -> str:
    """Return an opaque digest of answer-affecting, non-secret settings."""
    payload = {field: getattr(config, field) for field in _BEHAVIOR_FIELDS}
    payload["connection_key"] = _target_key(config.connection_string or "")
    payload["vector_store"] = (
        {
            "provider": config.vector_store.provider,
            "options": {
                key: _cache_option(key, value) for key, value in config.vector_store.options.items()
            },
        }
        if config.vector_store is not None
        else None
    )
    payload["turbovec_index_dir"] = config.turbovec_index_dir
    schema = config.output_model
    if schema is not None:
        payload["output_model"] = (
            f"{schema.__module__}.{schema.__qualname__}"
            if isinstance(schema, type)
            else type(schema).__qualname__
        )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _target_key(value: str) -> str:
    """Hash endpoint identity without user info, query credentials, or fragments."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme and parsed.hostname:
            target = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or ''}{parsed.path}"
        else:
            target = value
    except ValueError:
        target = value
    return hashlib.sha256(target.encode("utf-8")).hexdigest()


def _cache_option(key: str, value: object) -> object:
    normalized = key.casefold().replace("-", "_")
    if any(
        secret in normalized
        for secret in ("secret", "password", "token", "api_key", "credential", "auth")
    ):
        return "[redacted]"
    if normalized in ("url", "endpoint", "dsn", "connection_string") and isinstance(value, str):
        return _target_key(value)
    return value
