"""In-memory evaluation for typed TurboVec metadata filters."""

from __future__ import annotations

from collections.abc import Mapping

from docpipe.plugins.contracts.vectorstore import And, Equals, FilterExpression, In, Not, Or, Range


def matches_filter(metadata: Mapping[str, object], expression: FilterExpression | None) -> bool:
    """Return whether metadata satisfies a validated filter expression."""
    if expression is None:
        return True
    if isinstance(expression, Equals):
        found, value = _lookup(metadata, expression.field)
        return found and _equal_scalar(value, expression.value)
    if isinstance(expression, In):
        found, value = _lookup(metadata, expression.field)
        return found and any(_equal_scalar(value, candidate) for candidate in expression.values)
    if isinstance(expression, Range):
        found, value = _lookup(metadata, expression.field)
        return found and _matches_range(value, expression)
    if isinstance(expression, And):
        return all(matches_filter(metadata, child) for child in expression.expressions)
    if isinstance(expression, Or):
        return any(matches_filter(metadata, child) for child in expression.expressions)
    if isinstance(expression, Not):
        return not matches_filter(metadata, expression.expression)
    raise TypeError("unsupported vector filter expression")


def _lookup(metadata: Mapping[str, object], field: str) -> tuple[bool, object]:
    current: object = metadata
    for component in field.split("."):
        if not isinstance(current, Mapping) or component not in current:
            return False, None
        current = current[component]
    return True, current


def _equal_scalar(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def _matches_range(value: object, expression: Range) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return (
        (expression.gt is None or value > expression.gt)
        and (expression.gte is None or value >= expression.gte)
        and (expression.lt is None or value < expression.lt)
        and (expression.lte is None or value <= expression.lte)
    )
