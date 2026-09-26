"""Domain models and errors have stable, discoverable homes."""

from __future__ import annotations


def should_locate_provider_models_in_schema_modules() -> None:
    from docpipe.sources.s3 import configuration as s3_configuration
    from docpipe.sources.s3.schemas import S3SourceConfig
    from docpipe.vectorstores.qdrant import configuration as qdrant_configuration
    from docpipe.vectorstores.qdrant.schemas import QdrantConfig

    assert S3SourceConfig.__module__ == "docpipe.sources.s3.schemas"
    assert QdrantConfig.__module__ == "docpipe.vectorstores.qdrant.schemas"
    assert s3_configuration.S3SourceConfig is S3SourceConfig
    assert qdrant_configuration.QdrantConfig is QdrantConfig


def should_locate_ingestion_exceptions_in_errors_module() -> None:
    from docpipe.ingestion import coordinator, incremental
    from docpipe.ingestion.errors import IncompleteIngestionError, IncrementalStateError

    assert IncompleteIngestionError.__module__ == "docpipe.ingestion.errors"
    assert IncrementalStateError.__module__ == "docpipe.ingestion.errors"
    assert coordinator.IncompleteIngestionError is IncompleteIngestionError
    assert incremental.IncrementalStateError is IncrementalStateError


def should_locate_manifest_and_operation_errors_in_errors_modules() -> None:
    from docpipe.core.errors import OperationDeadlineExceededError
    from docpipe.core.operation import OperationDeadlineExceededError as LegacyOperationError
    from docpipe.plugins.errors import ManifestValidationError
    from docpipe.plugins.manifest import ManifestValidationError as LegacyManifestError

    assert OperationDeadlineExceededError is LegacyOperationError
    assert ManifestValidationError is LegacyManifestError


def should_split_public_models_by_domain_without_breaking_legacy_imports() -> None:
    from docpipe.core import types
    from docpipe.core.schemas.documents import ParsedDocument
    from docpipe.core.schemas.evaluation import EvalResult
    from docpipe.core.schemas.extraction import ExtractionResult
    from docpipe.core.schemas.ingestion import IngestionConfig
    from docpipe.core.schemas.rag import RAGConfig

    for legacy, canonical in (
        (types.ParsedDocument, ParsedDocument),
        (types.ExtractionResult, ExtractionResult),
        (types.IngestionConfig, IngestionConfig),
        (types.RAGConfig, RAGConfig),
        (types.EvalResult, EvalResult),
    ):
        assert legacy is canonical
        assert canonical.__module__.startswith("docpipe.core.schemas.")
