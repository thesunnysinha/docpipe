"""Qdrant result translation keeps backend counts inside the domain contract."""

from __future__ import annotations

import pytest

from docpipe.plugins.errors import VectorStoreOperationError
from docpipe.vectorstores.qdrant.responses import validate_point_count


def should_accept_a_non_negative_integer_point_count() -> None:
    assert validate_point_count(7) == 7


@pytest.mark.parametrize("value", [True, -1, 1.5, "7", None])
def should_reject_malformed_point_counts_without_exposing_backend_values(
    value: object,
) -> None:
    with pytest.raises(VectorStoreOperationError) as raised:
        validate_point_count(value)

    assert raised.value.context == {"provider": "qdrant", "operation": "delete_by_source"}
    assert str(value) not in str(raised.value)
