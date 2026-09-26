"""Tests for parameterized pgvector metadata filters."""

from __future__ import annotations

from docpipe.plugins.contracts.vectorstore import And, Equals, In, Not, Or, Range
from docpipe.vectorstores.pgvector.filters import compile_filter


def test_filter_compiler_parameterizes_fields_and_values() -> None:
    expression = And(
        (
            Equals("tenant.id", "tenant-1"),
            In("status", ("open", "paid")),
            Range("amount", gte=10, lt=100),
            Not(Or((Equals("deleted", True), Equals("kind", "draft")))),
        )
    )

    compiled = compile_filter(expression)

    assert "tenant-1" not in compiled.sql
    assert "open" not in compiled.sql
    assert "amount" not in compiled.sql
    assert compiled.sql.count("%s") == len(compiled.parameters)
    assert compiled.parameters[0] == ["tenant", "id"]


def test_absent_filter_compiles_to_identity() -> None:
    compiled = compile_filter(None)

    assert compiled.sql == "TRUE"
    assert compiled.parameters == ()
