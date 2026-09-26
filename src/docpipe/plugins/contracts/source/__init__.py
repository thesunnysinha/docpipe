"""Public vendor-neutral source resolver and handle contracts."""

from docpipe.plugins.contracts.source.handle import ManagedSourceHandle, ResolvedSourceHandle
from docpipe.plugins.contracts.source.models import SourceDescriptor, is_valid_media_type
from docpipe.plugins.contracts.source.resolver import SourceResolver

__all__ = [
    "ManagedSourceHandle",
    "ResolvedSourceHandle",
    "SourceDescriptor",
    "SourceResolver",
    "is_valid_media_type",
]
