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
    "lightrag_working_dir",
    "system_prompt",
    "history",
    "response_format",
    "filters",
    "vector_backend",
    "turbovec_bit_width",
)


def cache_namespace(config: RAGConfig, *, tenant_scope: str | None = None) -> str:
    """Return an opaque digest of answer-affecting settings and access scope.

    Credential fingerprints prevent two provider accounts that happen to use
    the same model name from sharing answers. The credentials themselves are
    never included in the serialized namespace or emitted to logs.
    """
    payload: dict[str, object] = {"schema_version": 1}
    payload.update({field: getattr(config, field) for field in _BEHAVIOR_FIELDS})
    payload["connection_key"] = _target_key(config.connection_string or "")
    payload["connection_credential"] = _secret_fingerprint(config.connection_string)
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
    payload["tenant_scope"] = tenant_scope
    payload["embedding_credential"] = _secret_fingerprint(config.embedding_api_key)
    payload["llm_credential"] = _secret_fingerprint(config.llm_api_key)
    schema = config.output_model
    if schema is not None:
        payload["output_model"] = (
            f"{schema.__module__}.{schema.__qualname__}"
            if isinstance(schema, type)
            else type(schema).__qualname__
        )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cache_key(config: RAGConfig, question: str, *, tenant_scope: str | None = None) -> str:
    """Build an opaque exact-question KV key; never expose question text."""
    namespace = cache_namespace(config, tenant_scope=tenant_scope)
    question_digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    return hashlib.sha256(f"{namespace}:{question_digest}".encode("ascii")).hexdigest()


def _secret_fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        return _secret_fingerprint(str(value))
    if normalized in ("url", "endpoint", "dsn", "connection_string") and isinstance(value, str):
        # Endpoint-only identity is insufficient for permission-aware stores:
        # different database users can see different rows at the same target.
        # Keep both a credential-free target digest and a digest of the full
        # connection value; neither raw credentials nor DSNs leave this helper.
        return {
            "target": _target_key(value),
            "credential": _secret_fingerprint(value),
        }
    if isinstance(value, dict):
        return {
            str(child_key): _cache_option(str(child_key), child_value)
            for child_key, child_value in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_cache_option(key, child_value) for child_value in value]
    return value
