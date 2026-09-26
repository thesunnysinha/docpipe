"""Public conformance helpers for Docpipe plugin authors."""

from docpipe.testing.sources import assert_source_conformance
from docpipe.testing.vectorstores import assert_binding_shape, assert_vector_store_conformance

__all__ = [
    "assert_binding_shape",
    "assert_source_conformance",
    "assert_vector_store_conformance",
]
