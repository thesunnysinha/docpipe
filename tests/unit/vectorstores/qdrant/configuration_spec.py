"""Qdrant configuration stays typed and secret-safe."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docpipe.vectorstores.qdrant.configuration import QdrantConfig


def should_require_one_location_and_safe_collection() -> None:
    remote = QdrantConfig(url="https://vectors.example", collection="reports")
    local = QdrantConfig(location=":memory:", collection="reports")

    assert remote.collection == "reports"
    assert local.location == ":memory:"
    with pytest.raises(ValidationError):
        QdrantConfig(url="https://vectors.example", location=":memory:")
    with pytest.raises(ValidationError):
        QdrantConfig(url="https://vectors.example", collection="../../bad")
    with pytest.raises(ValidationError):
        QdrantConfig(url="http://vectors.example")


def should_enforce_bounded_scan_and_timeout() -> None:
    with pytest.raises(ValidationError):
        QdrantConfig(location=":memory:", timeout_seconds=0)
    with pytest.raises(ValidationError):
        QdrantConfig(location=":memory:", max_scan_points=0)
