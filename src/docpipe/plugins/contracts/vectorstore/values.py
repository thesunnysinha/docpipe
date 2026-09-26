"""Validation and immutable normalization for vector boundary values."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import TypeAlias

JsonScalar: TypeAlias = None | bool | int | float | str
FrozenJson: TypeAlias = JsonScalar | tuple["FrozenJson", ...] | Mapping[str, "FrozenJson"]


def normalize_vector(vector: Sequence[object], *, field_name: str = "vector") -> tuple[float, ...]:
    """Return an immutable finite vector or fail at the boundary."""
    if not vector:
        raise ValueError(f"{field_name} must not be empty")
    normalized: list[float] = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} values must be numbers")
        item = float(value)
        if not math.isfinite(item):
            raise ValueError(f"{field_name} values must be finite")
        normalized.append(item)
    return tuple(normalized)


def freeze_metadata(metadata: Mapping[str, object]) -> Mapping[str, FrozenJson]:
    """Validate and detach recursive JSON metadata."""
    try:
        return MappingProxyType({str(key): _freeze_json(value) for key, value in metadata.items()})
    except (TypeError, ValueError) as exc:
        raise type(exc)(f"metadata contains an unsupported value: {exc}") from exc


def validate_number(value: object, *, field_name: str) -> None:
    """Reject booleans and non-finite numeric values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite number")


def validate_scalar(value: object, *, field_name: str) -> None:
    """Validate a JSON scalar without coercion."""
    if not (value is None or isinstance(value, (bool, int, float, str))):
        raise TypeError(f"{field_name} must be a JSON scalar")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")


def _freeze_json(value: object) -> FrozenJson:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("mapping keys must be strings")
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_json(item) for item in value)
    raise TypeError(f"unsupported {type(value).__name__}")
