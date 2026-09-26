"""Tests for stable and safe plugin exceptions."""

from __future__ import annotations

from docpipe.plugins.errors import (
    CollectionNotFoundError,
    PluginCapabilityError,
    PluginConfigurationError,
    PluginDependencyError,
    PluginError,
    PluginNotFoundError,
    PluginOperationError,
    RetryClassification,
    SourceAccessError,
    SourceError,
    SourceTooLargeError,
    UnsafeSourceError,
    UnsupportedSourceError,
    VectorStoreConnectionError,
    VectorStoreError,
    VectorStoreOperationError,
)


def test_plugin_error_serializes_stable_safe_fields() -> None:
    error = PluginDependencyError(
        "qdrant is not installed",
        plugin="qdrant",
        hint="Install docpipe-sdk[qdrant]",
        context={"api_key": "secret", "attempt": 1},
    )

    assert error.to_dict() == {
        "code": "plugin_dependency_missing",
        "message": "qdrant is not installed",
        "retry": RetryClassification.NEVER.value,
        "plugin": "qdrant",
        "hint": "Install docpipe-sdk[qdrant]",
        "context": {"api_key": "[REDACTED]", "attempt": 1},
    }


def test_plugin_error_preserves_cause_without_serializing_it() -> None:
    cause = RuntimeError("password=secret")
    try:
        raise PluginDependencyError("dependency failed", plugin="qdrant") from cause
    except PluginDependencyError as error:
        assert error.__cause__ is cause
        assert "password" not in str(error.to_dict())


def test_public_error_hierarchy_is_vendor_independent() -> None:
    assert issubclass(PluginNotFoundError, PluginError)
    assert issubclass(PluginConfigurationError, PluginError)
    assert issubclass(PluginCapabilityError, PluginError)
    assert issubclass(PluginOperationError, PluginError)
    assert issubclass(UnsupportedSourceError, SourceError)
    assert issubclass(SourceAccessError, SourceError)
    assert issubclass(SourceTooLargeError, SourceError)
    assert issubclass(UnsafeSourceError, SourceError)
    assert issubclass(VectorStoreConnectionError, VectorStoreError)
    assert issubclass(CollectionNotFoundError, VectorStoreError)
    assert issubclass(VectorStoreOperationError, VectorStoreError)


def test_retry_classification_has_stable_values() -> None:
    assert {item.value for item in RetryClassification} == {
        "never",
        "transient",
        "throttled",
        "unknown",
    }
