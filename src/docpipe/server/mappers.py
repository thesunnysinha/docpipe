"""Map API request schemas to core domain objects."""

from __future__ import annotations

from docpipe.core.types import ExtractionSchema
from docpipe.schemas import ExtractRequest, RunRequest


def extraction_schema_from_request(req: ExtractRequest | RunRequest) -> ExtractionSchema:
    """Map public extraction request fields to the core schema contract."""
    return ExtractionSchema(
        description=req.description,
        model_id=req.model_id,
        examples=req.examples,
        entity_classes=req.entity_classes,
        strict=getattr(req, "strict", True),
    )
