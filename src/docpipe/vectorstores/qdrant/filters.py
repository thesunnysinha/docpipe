"""Compile vendor-neutral predicates to Qdrant payload filters."""

from __future__ import annotations

from qdrant_client import models

from docpipe.plugins.contracts.vectorstore import And, Equals, FilterExpression, In, Not, Or, Range


def compile_filter(expression: FilterExpression) -> models.Filter:
    """Compile recursively, keeping vendor models inside this adapter package."""
    if isinstance(expression, And):
        return models.Filter(must=[_condition(item) for item in expression.expressions])
    if isinstance(expression, Or):
        return models.Filter(should=[_condition(item) for item in expression.expressions])
    if isinstance(expression, Not):
        return models.Filter(must_not=[_condition(expression.expression)])
    return models.Filter(must=[_condition(expression)])


def _condition(expression: FilterExpression) -> models.Filter | models.FieldCondition:
    if isinstance(expression, (And, Or, Not)):
        return compile_filter(expression)
    key = f"metadata.{expression.field}"
    if isinstance(expression, Equals):
        if expression.value is None:
            return models.FieldCondition(key=key, is_null=True)
        if isinstance(expression.value, float):
            return models.FieldCondition(
                key=key,
                range=models.Range(gte=expression.value, lte=expression.value),
            )
        return models.FieldCondition(key=key, match=models.MatchValue(value=expression.value))
    if isinstance(expression, Range):
        return models.FieldCondition(
            key=key,
            range=models.Range(
                gt=expression.gt,
                gte=expression.gte,
                lt=expression.lt,
                lte=expression.lte,
            ),
        )
    if isinstance(expression, In):
        return models.Filter(
            should=[_condition(Equals(expression.field, value)) for value in expression.values]
        )
    raise TypeError("unsupported vector filter expression")
