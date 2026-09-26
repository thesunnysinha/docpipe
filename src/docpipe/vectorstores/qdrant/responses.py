"""Validate Qdrant response values before they enter Docpipe contracts."""

from docpipe.plugins.errors import VectorStoreOperationError


def validate_point_count(value: object) -> int:
    """Return a valid exact-delete count from an untyped SDK response.

    Args:
        value: The ``count`` value returned by the selected Qdrant SDK client.

    Returns:
        The non-negative exact point count.

    Raises:
        VectorStoreOperationError: If the SDK response is not a non-negative integer.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VectorStoreOperationError(
            "Qdrant returned an invalid point count",
            context={"provider": "qdrant", "operation": "delete_by_source"},
        )
    return value
