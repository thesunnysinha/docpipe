"""Public vector-store models and segregated facets."""

from docpipe.plugins.contracts.vectorstore.admin import VectorCollectionAdmin
from docpipe.plugins.contracts.vectorstore.capabilities import (
    PluginHealthProbe,
    VectorCapability,
    VectorStoreBinding,
)
from docpipe.plugins.contracts.vectorstore.filters import (
    And,
    Equals,
    FilterExpression,
    In,
    Not,
    Or,
    Range,
)
from docpipe.plugins.contracts.vectorstore.models import (
    CollectionRef,
    SourceAggregate,
    VectorMatch,
    VectorQuery,
    VectorQueryKind,
    VectorRecord,
    WriteBatch,
    WriteBatchResult,
)
from docpipe.plugins.contracts.vectorstore.reader import VectorReader
from docpipe.plugins.contracts.vectorstore.writer import VectorWriter

__all__ = [
    "And",
    "CollectionRef",
    "Equals",
    "FilterExpression",
    "In",
    "Not",
    "Or",
    "PluginHealthProbe",
    "Range",
    "SourceAggregate",
    "VectorCapability",
    "VectorCollectionAdmin",
    "VectorMatch",
    "VectorQuery",
    "VectorQueryKind",
    "VectorReader",
    "VectorRecord",
    "VectorStoreBinding",
    "VectorWriter",
    "WriteBatch",
    "WriteBatchResult",
]
