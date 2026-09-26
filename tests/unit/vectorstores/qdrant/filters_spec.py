"""Typed Docpipe predicates compile into Qdrant model objects."""

from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client")

from qdrant_client import models

from docpipe.plugins.contracts.vectorstore import And, Equals, In, Not, Or, Range
from docpipe.vectorstores.qdrant.filters import compile_filter


def should_compile_filters_into_metadata_namespace() -> None:
    compiled = compile_filter(And((Equals("kind", "report"), Range("score", gte=1, lt=5))))

    assert isinstance(compiled, models.Filter)
    assert compiled.must is not None
    assert compiled.must[0].key == "metadata.kind"
    assert compiled.must[1].key == "metadata.score"


def should_compile_or_not_null_and_numeric_membership() -> None:
    compiled = compile_filter(Or((Not(Equals("missing", None)), In("rating", (1.5, 2.5)))))

    assert isinstance(compiled, models.Filter)
    assert compiled.should is not None
    assert len(compiled.should) == 2
