"""Tests for vendor-neutral vector-store domain models."""

from __future__ import annotations

import math

import pytest

from docpipe.plugins.contracts.vectorstore import (
    And,
    CollectionRef,
    Equals,
    In,
    Range,
    VectorQuery,
    VectorQueryKind,
    VectorRecord,
    WriteBatch,
    WriteBatchResult,
)


def test_vector_record_normalizes_immutable_values() -> None:
    metadata = {"page": 1, "nested": {"published": True}}
    record = VectorRecord(
        record_id="  doc-1  ",
        text="content",
        vector=[1, 2.5],
        metadata=metadata,
        source_id=" report.pdf ",
    )
    metadata["page"] = 9

    assert record.record_id == "doc-1"
    assert record.vector == (1.0, 2.5)
    assert record.metadata["page"] == 1
    assert record.source_id == "report.pdf"
    with pytest.raises(AttributeError):
        record.text = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("vector", [[], [math.nan], [math.inf], ["bad"]])
def test_vector_record_rejects_invalid_vectors(vector: list[object]) -> None:
    with pytest.raises((TypeError, ValueError), match="vector"):
        VectorRecord(record_id="doc-1", text="content", vector=vector)


def test_models_reject_unsafe_names_and_non_json_metadata() -> None:
    with pytest.raises(ValueError, match="collection"):
        CollectionRef("docs; DROP TABLE vectors")
    with pytest.raises((TypeError, ValueError), match="metadata"):
        VectorRecord(record_id="doc-1", text="content", vector=[1.0], metadata={"x": object()})


def test_typed_filters_compose_without_raw_vendor_syntax() -> None:
    filter_expression = And(
        (
            Equals("document.type", "invoice"),
            In("status", ("open", "paid")),
            Range("amount", gte=10, lt=100),
        )
    )
    query = VectorQuery(
        collection=CollectionRef("documents"),
        dense_vector=[0.1],
        filter=filter_expression,
    )

    assert query.filter == filter_expression
    with pytest.raises(TypeError, match="filter"):
        VectorQuery(collection=CollectionRef("documents"), dense_vector=[0.1], filter="vendor")


def test_vector_query_distinguishes_dense_sparse_and_hybrid() -> None:
    collection = CollectionRef("documents")

    assert VectorQuery(collection, dense_vector=[1.0]).kind is VectorQueryKind.DENSE
    assert VectorQuery(collection, sparse_vector={2: 0.5}).kind is VectorQueryKind.SPARSE
    assert (
        VectorQuery(collection, dense_vector=[1.0], sparse_vector={2: 0.5}).kind
        is VectorQueryKind.HYBRID
    )


def test_write_batch_result_requires_consistent_accounting() -> None:
    record = VectorRecord(record_id="one", text="text", vector=[1.0])
    batch = WriteBatch(CollectionRef("documents"), (record,))

    assert batch.records == (record,)
    assert WriteBatchResult(requested=1, accepted=1).accepted == 1
    with pytest.raises(ValueError, match="sum"):
        WriteBatchResult(requested=2, accepted=1)
