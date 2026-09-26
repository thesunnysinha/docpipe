"""Tests for typed in-memory TurboVec metadata filtering."""

from docpipe.plugins.contracts.vectorstore import And, Equals, In, Not, Or, Range
from docpipe.vectorstores.turbovec.filters import matches_filter


def test_nested_scalar_and_range_filters() -> None:
    metadata = {"tenant": {"name": "acme"}, "page": 7, "published": True}

    assert matches_filter(metadata, Equals("tenant.name", "acme"))
    assert matches_filter(metadata, In("page", (6, 7)))
    assert matches_filter(metadata, Range("page", gte=7, lt=8))
    assert not matches_filter(metadata, Equals("published", 1))


def test_boolean_filters_and_missing_fields_are_deterministic() -> None:
    metadata = {"kind": "invoice", "page": 2}
    expression = And(
        (
            Or((Equals("kind", "receipt"), Equals("kind", "invoice"))),
            Not(Range("page", gt=2)),
        )
    )

    assert matches_filter(metadata, expression)
    assert not matches_filter(metadata, Equals("missing.field", None))
