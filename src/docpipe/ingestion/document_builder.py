"""Build immutable Docpipe ingestion documents from parsed domain models."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from docpipe.core.types import ExtractionResult, ParsedDocument
from docpipe.ingestion.configuration import IngestMode
from docpipe.plugins.contracts.vectorstore.values import FrozenJson, freeze_metadata


@dataclass(frozen=True, slots=True)
class IngestionDocument:
    """Text and provenance awaiting chunking and vector encoding."""

    record_id: str
    text: str
    metadata: Mapping[str, object]
    source_id: str

    def __post_init__(self) -> None:
        """Normalize identity and detach recursive metadata."""
        if not self.record_id.strip() or not self.source_id.strip():
            raise ValueError("ingestion document identifiers must not be empty")
        if not isinstance(self.text, str):
            raise TypeError("ingestion document text must be a string")
        frozen: Mapping[str, FrozenJson] = freeze_metadata(self.metadata)
        object.__setattr__(self, "metadata", frozen)

    def with_text(self, text: str) -> IngestionDocument:
        """Return a copy containing transformed text."""
        return replace(self, text=text)

    def with_metadata(self, values: Mapping[str, object]) -> IngestionDocument:
        """Return a copy with validated metadata additions."""
        return replace(self, metadata={**self.metadata, **values})


class DocumentBuilder:
    """Normalize parsed pages and extractions without framework objects."""

    def __init__(self, mode: IngestMode) -> None:
        self._mode = mode

    def build(
        self,
        parsed: ParsedDocument,
        extractions: Sequence[ExtractionResult] | None = None,
    ) -> tuple[IngestionDocument, ...]:
        """Build selected representations in stable input order."""
        documents: list[IngestionDocument] = []
        if self._mode in (IngestMode.CHUNKS, IngestMode.BOTH):
            documents.extend(self._parsed_documents(parsed))
        if self._mode in (IngestMode.EXTRACTIONS, IngestMode.BOTH):
            documents.extend(self._extraction_documents(parsed.source, extractions or ()))
        return tuple(documents)

    @staticmethod
    def _parsed_documents(parsed: ParsedDocument) -> tuple[IngestionDocument, ...]:
        page_documents = tuple(
            _document(
                source=parsed.source,
                kind="parsed",
                ordinal=page.page_number,
                text=page.text,
                metadata={
                    "source": parsed.source,
                    "page": page.page_number,
                    "source_type": "parsed",
                },
            )
            for page in parsed.pages
            if page.text.strip()
        )
        if page_documents:
            return page_documents
        if not parsed.text.strip():
            return ()
        return (
            _document(
                source=parsed.source,
                kind="parsed",
                ordinal=0,
                text=parsed.text,
                metadata={"source": parsed.source, "source_type": "parsed"},
            ),
        )

    @staticmethod
    def _extraction_documents(
        source: str,
        extractions: Sequence[ExtractionResult],
    ) -> tuple[IngestionDocument, ...]:
        return tuple(
            _document(
                source=source,
                kind="extraction",
                ordinal=index,
                text=f"{extraction.entity_class}: {extraction.text}",
                metadata={
                    "source": source,
                    "source_type": "extraction",
                    "entity_class": extraction.entity_class,
                    **extraction.attributes,
                },
            )
            for index, extraction in enumerate(extractions)
        )


def _document(
    *,
    source: str,
    kind: str,
    ordinal: int,
    text: str,
    metadata: Mapping[str, object],
) -> IngestionDocument:
    digest = hashlib.sha256()
    for value in (source, kind, str(ordinal), text):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return IngestionDocument(
        record_id=digest.hexdigest(),
        text=text,
        metadata=metadata,
        source_id=source,
    )
