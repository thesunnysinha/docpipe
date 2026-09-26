"""Typed, vendor-neutral vector metadata filter expressions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypeAlias

from docpipe.plugins.contracts.vectorstore.values import (
    JsonScalar,
    validate_number,
    validate_scalar,
)

_FIELD_PATH = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*")


@dataclass(frozen=True, slots=True)
class Equals:
    """Match one metadata field to a scalar value."""

    field: str
    value: JsonScalar

    def __post_init__(self) -> None:
        _validate_field(self.field)
        validate_scalar(self.value, field_name="filter value")


@dataclass(frozen=True, slots=True)
class In:
    """Match one metadata field against a non-empty scalar set."""

    field: str
    values: tuple[JsonScalar, ...]

    def __post_init__(self) -> None:
        _validate_field(self.field)
        object.__setattr__(self, "values", tuple(self.values))
        if not self.values:
            raise ValueError("filter membership values must not be empty")
        for value in self.values:
            validate_scalar(value, field_name="filter value")


@dataclass(frozen=True, slots=True)
class Range:
    """Numeric range over a metadata field."""

    field: str
    gt: float | int | None = None
    gte: float | int | None = None
    lt: float | int | None = None
    lte: float | int | None = None

    def __post_init__(self) -> None:
        _validate_field(self.field)
        bounds = (self.gt, self.gte, self.lt, self.lte)
        if all(value is None for value in bounds):
            raise ValueError("range filter requires at least one bound")
        for value in bounds:
            if value is not None:
                validate_number(value, field_name="range bound")


@dataclass(frozen=True, slots=True)
class And:
    """Require every child filter to match."""

    expressions: tuple[FilterExpression, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "expressions", tuple(self.expressions))
        _validate_expressions(self.expressions)


@dataclass(frozen=True, slots=True)
class Or:
    """Require at least one child filter to match."""

    expressions: tuple[FilterExpression, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "expressions", tuple(self.expressions))
        _validate_expressions(self.expressions)


@dataclass(frozen=True, slots=True)
class Not:
    """Negate one child filter."""

    expression: FilterExpression

    def __post_init__(self) -> None:
        if not is_filter(self.expression):
            raise TypeError("filter expression must be a typed filter node")


FilterExpression: TypeAlias = Equals | In | Range | And | Or | Not


def is_filter(value: object) -> bool:
    """Return whether a value is a supported typed filter node."""
    return isinstance(value, (Equals, In, Range, And, Or, Not))


def _validate_field(field_name: str) -> None:
    if _FIELD_PATH.fullmatch(field_name) is None:
        raise ValueError("filter field must be a safe dotted identifier")


def _validate_expressions(expressions: tuple[FilterExpression, ...]) -> None:
    if not expressions:
        raise ValueError("boolean filter requires at least one expression")
    if not all(is_filter(expression) for expression in expressions):
        raise TypeError("boolean filter contains an invalid filter expression")
