"""Stable ingestion failures shared by orchestration and compatibility APIs."""

from __future__ import annotations

from docpipe.core.errors import IngestionError
from docpipe.plugins.contracts.vectorstore import WriteBatchResult


class IncrementalStateError(IngestionError):
    """Raised when duplicate state cannot be checked under fail-closed policy."""


class IncompleteIngestionError(IngestionError):
    """Raised when a vector write cannot confirm that the whole batch was accepted.

    The exception exposes batch counts so callers can distinguish rejected records
    from outcomes that are uncertain and may require reconciliation.
    """

    def __init__(self, result: WriteBatchResult) -> None:
        """Create an error retaining write counts for recovery logic.

        Args:
            result: Vector-store result describing requested, accepted, rejected,
                and uncertain record counts.
        """
        super().__init__("vector store did not confirm the complete ingestion batch")
        self.requested = result.requested
        self.accepted = result.accepted
        self.rejected = result.rejected
        self.uncertain = result.uncertain
