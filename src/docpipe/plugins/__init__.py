"""Stable public primitives for Docpipe plugins."""

from docpipe.plugins.api_version import DOCPIPE_PLUGIN_API_VERSION, PluginApiVersion
from docpipe.plugins.catalog import (
    PluginCatalog,
    PluginCatalogBuilder,
    PluginOrigin,
    PluginRegistration,
)
from docpipe.plugins.configuration import PluginConfig, TypedPluginConfig
from docpipe.plugins.credentials import (
    CredentialResolver,
    EnvironmentCredentialResolver,
    SecretReference,
)
from docpipe.plugins.descriptors import (
    PluginCategory,
    PluginDescriptor,
    PluginRequirement,
    PluginStability,
    RuntimeRequirement,
)
from docpipe.plugins.errors import (
    CollectionNotFoundError,
    PluginCapabilityError,
    PluginConfigurationError,
    PluginDependencyError,
    PluginError,
    PluginNotFoundError,
    PluginOperationError,
    PluginPolicyError,
    PluginRegistrationConflictError,
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

__all__ = [
    "DOCPIPE_PLUGIN_API_VERSION",
    "CollectionNotFoundError",
    "CredentialResolver",
    "EnvironmentCredentialResolver",
    "PluginApiVersion",
    "PluginCatalog",
    "PluginCatalogBuilder",
    "PluginCapabilityError",
    "PluginCategory",
    "PluginConfig",
    "PluginConfigurationError",
    "PluginDependencyError",
    "PluginDescriptor",
    "PluginError",
    "PluginNotFoundError",
    "PluginOperationError",
    "PluginOrigin",
    "PluginPolicyError",
    "PluginRegistration",
    "PluginRegistrationConflictError",
    "PluginRequirement",
    "PluginStability",
    "RetryClassification",
    "RuntimeRequirement",
    "SecretReference",
    "SourceAccessError",
    "SourceError",
    "SourceTooLargeError",
    "TypedPluginConfig",
    "UnsafeSourceError",
    "UnsupportedSourceError",
    "VectorStoreConnectionError",
    "VectorStoreError",
    "VectorStoreOperationError",
]
