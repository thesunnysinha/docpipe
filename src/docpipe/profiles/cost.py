"""Heuristic ingest cost and latency estimates per runtime preset."""

from __future__ import annotations

from typing import Any

from docpipe.profiles.catalog import RUNTIME_PRESETS

# Seconds per page at P50 — tuned for planning, not billing.
_PARSE_SECONDS_PER_PAGE: dict[str, float] = {
    "fast": 0.4,
    "balanced": 1.2,
    "quality": 4.5,
    "agents": 1.2,
}

# USD per 1k embedding tokens (OpenAI text-embedding-3-small baseline).
_EMBED_USD_PER_1K_TOKENS: dict[str, float] = {
    "openai": 0.00002,
    "google": 0.00001,
    "ollama": 0.0,
    "huggingface": 0.0,
}

# Rough tokens per page after chunking.
_TOKENS_PER_PAGE: dict[str, int] = {
    "fast": 600,
    "balanced": 750,
    "quality": 900,
    "agents": 750,
}


def estimate_ingest_cost(
    *,
    preset: str,
    page_count: int,
    embedding_provider: str = "openai",
) -> dict[str, Any]:
    """Return parse time, embedding cost, and chunk estimates for a document ingest."""
    if page_count < 1:
        raise ValueError("page_count must be at least 1")

    preset_key = preset if preset in RUNTIME_PRESETS else "balanced"
    preset_meta = RUNTIME_PRESETS[preset_key]

    parse_seconds = round(_PARSE_SECONDS_PER_PAGE[preset_key] * page_count, 2)
    tokens = _TOKENS_PER_PAGE[preset_key] * page_count
    embed_rate = _EMBED_USD_PER_1K_TOKENS.get(embedding_provider.lower(), 0.00002)
    embedding_usd = round((tokens / 1000) * embed_rate, 6)

    chunks_estimate = max(1, page_count * 3)
    total_usd = round(embedding_usd, 6)

    return {
        "preset": preset_key,
        "page_count": page_count,
        "embedding_provider": embedding_provider,
        "parser_tier": preset_meta.get("tier"),
        "chunker": preset_meta.get("chunker"),
        "estimated_parse_seconds": parse_seconds,
        "estimated_chunks": chunks_estimate,
        "estimated_embedding_tokens": tokens,
        "estimated_embedding_usd": embedding_usd,
        "estimated_total_usd": total_usd,
        "notes": (
            "Heuristic only — actual cost depends on document layout, parser choice, "
            "and embedding model pricing."
        ),
    }
