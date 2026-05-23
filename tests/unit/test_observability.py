"""Unit tests for observability configuration and helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from docpipe.config.settings import DocpipeSettings
from docpipe.observability.logging import configure_logging
from docpipe.observability.metrics import metrics_available, record_error, record_ingest
from docpipe.observability.spans import trace_operation
from docpipe.observability.tokens import extract_usage_from_langchain_response
from docpipe.observability.tracing import configure_observability


def test_configure_observability_disabled_by_default():
    import docpipe.observability.tracing as tracing_mod

    tracing_mod._CONFIGURED = False
    tracing_mod._TRACER = None
    settings = DocpipeSettings(otel_enabled=False)
    with patch("docpipe.config.get_settings", return_value=settings):
        tracing_mod._CONFIGURED = False
        tracing_mod._TRACER = None
        configure_observability()
        assert tracing_mod._TRACER is None


def test_trace_operation_noop_without_tracer():
    with trace_operation("docpipe.test") as span:
        assert span is None


def test_extract_usage_from_langchain_response():
    class FakeMessage:
        usage_metadata = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}

    usage = extract_usage_from_langchain_response(FakeMessage())
    assert usage is not None
    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
    assert usage.total_tokens == 15


def test_configure_logging_json_includes_request_id(capsys):
    import logging as stdlib_logging

    import docpipe.observability.logging as log_mod
    from docpipe.observability.request_context import bind_request_id, reset_request_id

    log_mod._CONFIGURED = False
    root = stdlib_logging.getLogger()
    root.handlers.clear()
    settings = DocpipeSettings(log_format="json", log_level="INFO")
    configure_logging(settings)
    token = bind_request_id("json-req-99")
    stdlib_logging.getLogger("docpipe.test.obs").info("hello json")
    reset_request_id(token)
    captured = capsys.readouterr().out.strip()
    assert '"request_id": "json-req-99"' in captured


def test_configure_logging_json(capsys):
    import logging as stdlib_logging

    import docpipe.observability.logging as log_mod

    log_mod._CONFIGURED = False
    root = stdlib_logging.getLogger()
    root.handlers.clear()
    settings = DocpipeSettings(log_format="json", log_level="INFO")
    configure_logging(settings)
    stdlib_logging.getLogger("docpipe.test.obs").info("hello json")
    captured = capsys.readouterr().out.strip()
    assert '"message": "hello json"' in captured


@pytest.mark.skipif(not metrics_available(), reason="prometheus-client not installed")
def test_record_ingest_and_errors():
    record_ingest("docs", 3)
    record_error("configuration", "parse", "/parse")


@pytest.mark.asyncio
async def test_request_response_logging_middleware():
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from docpipe.observability.middleware import RequestResponseLoggingMiddleware

    async def ping(_: object) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/rag/query", ping)])
    app.add_middleware(RequestResponseLoggingMiddleware)
    client = TestClient(app)
    response = client.get("/rag/query", headers={"X-Request-Id": "test-req-1"})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "test-req-1"
