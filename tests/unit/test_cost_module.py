"""Unit tests for profiles.cost heuristics."""

from __future__ import annotations

import pytest

from docpipe.profiles.cost import estimate_ingest_cost


def test_estimate_ingest_cost_quality_preset():
    result = estimate_ingest_cost(preset="quality", page_count=5, embedding_provider="openai")

    assert result["preset"] == "quality"
    assert result["estimated_parse_seconds"] == 22.5
    assert result["estimated_chunks"] == 15


def test_estimate_ingest_cost_invalid_pages():
    with pytest.raises(ValueError, match="page_count"):
        estimate_ingest_cost(preset="fast", page_count=0)
