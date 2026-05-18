from __future__ import annotations

from docpipe.core.errors import ConfigurationError, IngestionError, ParseError
from docpipe.server.http_errors import docpipe_http_exception


def test_configuration_error_is_400():
    exc = docpipe_http_exception(ConfigurationError("Unknown embedding provider: foo"))
    assert exc.status_code == 400
    assert exc.detail["error_type"] == "configuration"


def test_parse_error_is_400():
    exc = docpipe_http_exception(ParseError("Could not read PDF"))
    assert exc.status_code == 400
    assert exc.detail["phase"] == "parse"


def test_embedding_not_found_is_502_with_hint():
    msg = (
        "Failed to ingest into vector store: Error embedding content (NOT_FOUND): "
        "404 NOT_FOUND. models/embedding-001 is not found for API version v1beta"
    )
    exc = docpipe_http_exception(IngestionError(msg))
    assert exc.status_code == 502
    assert exc.detail["error_type"] == "upstream_provider"
    assert exc.detail["phase"] == "embedding"
    assert "text-embedding-004" in exc.detail["hint"]


def test_quota_exhausted_is_502():
    msg = "RESOURCE_EXHAUSTED: quota exceeded for generate_content"
    exc = docpipe_http_exception(IngestionError(msg))
    assert exc.status_code == 502
    assert exc.detail["error_type"] == "upstream_provider"
