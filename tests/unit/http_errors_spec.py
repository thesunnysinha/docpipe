from __future__ import annotations

from docpipe.core.errors import ConfigurationError, IngestionError, ParseError
from docpipe.plugins.errors import SourceAccessError, UnsafeSourceError
from docpipe.server.http_errors import docpipe_http_exception, integration_http_exception


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


def test_source_integration_errors_have_stable_safe_http_shape() -> None:
    unsafe = integration_http_exception(
        UnsafeSourceError("blocked https://host/doc?signature=private")
    )
    unavailable = integration_http_exception(SourceAccessError("upstream unavailable"))

    assert unsafe.status_code == 400
    assert unsafe.detail["code"] == "source_unsafe"
    assert "private" not in str(unsafe.detail)
    assert unavailable.status_code == 502
