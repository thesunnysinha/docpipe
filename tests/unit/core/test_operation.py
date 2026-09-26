"""Tests for immutable operation context and deadlines."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from docpipe.core.operation import OperationContext, OperationDeadlineExceededError
from docpipe.plugins.errors import RetryClassification


def test_operation_context_copies_trace_metadata_and_is_immutable() -> None:
    trace = {"traceparent": "00-abc"}
    context = OperationContext(request_id="req-1", tenant_id="tenant-7", trace_context=trace)
    trace["traceparent"] = "changed"

    assert context.trace_context["traceparent"] == "00-abc"
    with pytest.raises(AttributeError):
        context.request_id = "changed"  # type: ignore[misc]


def test_expired_deadline_has_stable_error_classification() -> None:
    context = OperationContext(
        request_id="req-1",
        deadline=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    with pytest.raises(OperationDeadlineExceededError) as caught:
        context.ensure_active()

    assert caught.value.code == "operation_deadline_exceeded"
    assert caught.value.retry is RetryClassification.NEVER


def test_deadline_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        OperationContext(request_id="req-1", deadline=datetime.now())
