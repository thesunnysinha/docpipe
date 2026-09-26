"""Stable public exceptions independent of optional vendor SDKs."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

from docpipe.plugins.redaction import RedactedValue, redact

REDACTED_MESSAGE = "integration operation failed"


class RetryClassification(str, Enum):
    """Whether an operation is safe to retry."""

    NEVER = "never"
    TRANSIENT = "transient"
    THROTTLED = "throttled"
    UNKNOWN = "unknown"


class PublicIntegrationError(Exception):
    """Base for safe, serializable integration failures."""

    code = "integration_error"
    default_retry = RetryClassification.UNKNOWN

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
        retry: RetryClassification | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        safe_message = redact(message)
        self.message = safe_message if isinstance(safe_message, str) else REDACTED_MESSAGE
        super().__init__(self.message)
        self.hint = hint
        self.context = dict(context or {})
        self.retry = retry or self.default_retry
        self.retry_after_seconds = retry_after_seconds

    def to_dict(self) -> dict[str, RedactedValue]:
        """Serialize stable fields after recursively redacting their values."""
        result: dict[str, RedactedValue] = {
            "code": self.code,
            "message": self.message,
            "retry": self.retry.value,
        }
        if self.hint is not None:
            result["hint"] = redact(self.hint)
        if self.context:
            result["context"] = redact(self.context)
        if self.retry_after_seconds is not None:
            result["retry_after_seconds"] = self.retry_after_seconds
        return result


class PluginError(PublicIntegrationError):
    """Base for plugin discovery, configuration, and operation failures."""

    def __init__(
        self,
        message: str,
        *,
        plugin: str | None = None,
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
        retry: RetryClassification | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(
            message,
            hint=hint,
            context=context,
            retry=retry,
            retry_after_seconds=retry_after_seconds,
        )
        self.plugin = plugin

    def to_dict(self) -> dict[str, RedactedValue]:
        """Include the stable plugin identifier when one is known."""
        result = super().to_dict()
        if self.plugin is not None:
            result["plugin"] = self.plugin
        return result


class PluginNotFoundError(PluginError):
    """Raised when no plugin matches a requested provider."""

    code = "plugin_not_found"
    default_retry = RetryClassification.NEVER


class PluginDependencyError(PluginError):
    """Raised when an optional plugin dependency is unavailable."""

    code = "plugin_dependency_missing"
    default_retry = RetryClassification.NEVER


class PluginConfigurationError(PluginError, ValueError):
    """Raised when plugin configuration is invalid."""

    code = "plugin_configuration_invalid"
    default_retry = RetryClassification.NEVER


class PluginCapabilityError(PluginError):
    """Raised when a plugin lacks a requested capability."""

    code = "plugin_capability_unsupported"
    default_retry = RetryClassification.NEVER


class PluginOperationError(PluginError):
    """Raised when a selected plugin cannot complete an operation."""

    code = "plugin_operation_failed"


class PluginRegistrationConflictError(PluginError):
    """Raised when two registrations claim the same category and name."""

    code = "plugin_registration_conflict"
    default_retry = RetryClassification.NEVER


class PluginPolicyError(PluginError):
    """Raised when configured policy does not permit loading a plugin."""

    code = "plugin_policy_denied"
    default_retry = RetryClassification.NEVER


class ManifestValidationError(ValueError):
    """Raised with a safe message when static manifest validation fails."""


class SourceError(PublicIntegrationError):
    """Base for source resolution and access failures."""


class UnsupportedSourceError(SourceError):
    """Raised when no resolver supports a source."""

    code = "source_unsupported"
    default_retry = RetryClassification.NEVER


class SourceAccessError(SourceError):
    """Raised when an otherwise supported source cannot be accessed."""

    code = "source_access_failed"


class SourceTooLargeError(SourceError):
    """Raised when a source exceeds an enforced size limit."""

    code = "source_too_large"
    default_retry = RetryClassification.NEVER


class UnsafeSourceError(SourceError):
    """Raised when source access would violate the configured security policy."""

    code = "source_unsafe"
    default_retry = RetryClassification.NEVER


class VectorStoreError(PublicIntegrationError):
    """Base for vector-store failures."""


class VectorStoreConnectionError(VectorStoreError):
    """Raised when a vector-store connection is unavailable."""

    code = "vectorstore_connection_failed"
    default_retry = RetryClassification.TRANSIENT


class CollectionNotFoundError(VectorStoreError):
    """Raised when a requested vector collection does not exist."""

    code = "vectorstore_collection_not_found"
    default_retry = RetryClassification.NEVER


class VectorStoreOperationError(VectorStoreError):
    """Raised when a vector-store operation fails."""

    code = "vectorstore_operation_failed"
