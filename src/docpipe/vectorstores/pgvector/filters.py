"""Parameterized SQL compilation for typed vector metadata filters."""

from __future__ import annotations

import json
from dataclasses import dataclass

from docpipe.plugins.contracts.vectorstore import And, Equals, FilterExpression, In, Not, Or, Range


@dataclass(frozen=True, slots=True)
class CompiledFilter:
    """SQL fragment and separately bound DB-API parameters."""

    sql: str
    parameters: tuple[object, ...]


def compile_filter(expression: FilterExpression | None) -> CompiledFilter:
    """Compile a typed expression without interpolating fields or values."""
    if expression is None:
        return CompiledFilter("TRUE", ())
    if isinstance(expression, Equals):
        return CompiledFilter(
            "metadata #> %s = %s::jsonb",
            (_field_path(expression.field), json.dumps(expression.value)),
        )
    if isinstance(expression, In):
        clauses = tuple("metadata #> %s = %s::jsonb" for _ in expression.values)
        parameters = tuple(
            item
            for value in expression.values
            for item in (_field_path(expression.field), json.dumps(value))
        )
        return CompiledFilter(f"({' OR '.join(clauses)})", parameters)
    if isinstance(expression, Range):
        return _compile_range(expression)
    if isinstance(expression, (And, Or)):
        operator = " AND " if isinstance(expression, And) else " OR "
        children = tuple(compile_filter(child) for child in expression.expressions)
        return CompiledFilter(
            f"({operator.join(child.sql for child in children)})",
            tuple(parameter for child in children for parameter in child.parameters),
        )
    if isinstance(expression, Not):
        child = compile_filter(expression.expression)
        return CompiledFilter(f"(NOT {child.sql})", child.parameters)
    raise TypeError("unsupported vector filter expression")


def _compile_range(expression: Range) -> CompiledFilter:
    clauses: list[str] = []
    parameters: list[object] = []
    for operator, value in (
        (">", expression.gt),
        (">=", expression.gte),
        ("<", expression.lt),
        ("<=", expression.lte),
    ):
        if value is None:
            continue
        clauses.append(f"(metadata #>> %s)::double precision {operator} %s")
        parameters.extend((_field_path(expression.field), value))
    return CompiledFilter(f"({' AND '.join(clauses)})", tuple(parameters))


def _field_path(field: str) -> list[str]:
    return field.split(".")
