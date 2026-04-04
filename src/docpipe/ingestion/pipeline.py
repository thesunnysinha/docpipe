"""Ingestion pipeline: chunk, embed, and store in user's vector DB."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from docpipe.core.errors import ConfigurationError, IngestionError
from docpipe.core.types import (
    ExtractionResult,
    IngestionConfig,
    IngestionResult,
    ParsedDocument,
)

logger = logging.getLogger(__name__)

EMBEDDING_PROVIDERS = {
    "openai": ("langchain_openai", "OpenAIEmbeddings", {"model": "model"}),
    "google": ("langchain_google_genai", "GoogleGenerativeAIEmbeddings", {"model": "model"}),
    "ollama": ("langchain_ollama", "OllamaEmbeddings", {"model": "model"}),
    "huggingface": ("langchain_huggingface", "HuggingFaceEmbeddings", {"model_name": "model"}),
}


class IngestionPipeline:
    """Orchestrates chunking, embedding, and vector store ingestion.

    Uses LangChain text splitters, embeddings, and PGVector.
    Does NOT manage any database - connects to user's existing DB.
    """

    def __init__(self, config: IngestionConfig) -> None:
        self._config = config
        self._embeddings = self._create_embeddings(config)
        self._splitter = self._create_splitter(config)

    def ingest(
        self,
        parsed: ParsedDocument,
        *,
        extractions: list[ExtractionResult] | None = None,
    ) -> IngestionResult:
        """Ingest parsed document and/or extractions into the user's vector DB.

        1. Convert to LangChain Documents based on ingest_mode
        2. Split into chunks
        3. Connect to user's DB via connection_string
        4. Embed and insert via PGVector
        """
        lc_docs: list[Any] = []
        mode = self._config.ingest_mode

        if mode in ("chunks", "both"):
            lc_docs.extend(self._parsed_to_lc_docs(parsed))

        if mode in ("extractions", "both") and extractions:
            lc_docs.extend(self._extractions_to_lc_docs(extractions, parsed.source))

        if not lc_docs:
            return IngestionResult(
                source=parsed.source,
                chunks_ingested=0,
                table_name=self._config.table_name,
                table_created=False,
            )

        # Incremental mode: skip if source hash already exists in the DB
        if self._config.incremental:
            source_hash = self._compute_source_hash(parsed.source)
            if self._hash_exists(source_hash):
                logger.info("Skipping %s (unchanged, incremental mode)", parsed.source)
                return IngestionResult(
                    source=parsed.source,
                    chunks_ingested=0,
                    skipped=1,
                    table_name=self._config.table_name,
                    table_created=False,
                )
            # Stamp all docs with the hash so future runs can detect them
            for doc in lc_docs:
                doc.metadata["source_hash"] = source_hash

        # Split documents into chunks
        chunks = self._splitter.split_documents(lc_docs)
        logger.info("Split into %d chunks from %d documents", len(chunks), len(lc_docs))

        # Ingest via LangChain PGVector
        try:
            from langchain_postgres import PGVector

            PGVector.from_documents(
                documents=chunks,
                embedding=self._embeddings,
                collection_name=self._config.table_name,
                connection=self._config.connection_string,
            )
            table_created = True
        except Exception as e:
            raise IngestionError(f"Failed to ingest into vector store: {e}") from e

        return IngestionResult(
            source=parsed.source,
            chunks_ingested=len(chunks),
            table_name=self._config.table_name,
            table_created=table_created,
        )

    async def aingest(
        self,
        parsed: ParsedDocument,
        *,
        extractions: list[ExtractionResult] | None = None,
    ) -> IngestionResult:
        """Async variant."""
        return await asyncio.to_thread(self.ingest, parsed, extractions=extractions)

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Similarity search against the user's vector DB."""
        try:
            from langchain_postgres import PGVector

            vectorstore = PGVector(
                embeddings=self._embeddings,
                collection_name=self._config.table_name,
                connection=self._config.connection_string,
            )
            results = vectorstore.similarity_search_with_score(query, k=top_k)
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                }
                for doc, score in results
            ]
        except Exception as e:
            raise IngestionError(f"Search failed: {e}") from e

    @staticmethod
    def _compute_source_hash(source: str) -> str:
        """SHA-256 of file bytes (or source string for non-file sources)."""
        try:
            with open(source, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return hashlib.sha256(source.encode()).hexdigest()

    def _hash_exists(self, source_hash: str) -> bool:
        """Check if a source_hash already exists in the vector store metadata."""
        try:
            from langchain_postgres import PGVector

            vs = PGVector(
                embeddings=self._embeddings,
                collection_name=self._config.table_name,
                connection=self._config.connection_string,
            )
            results = vs.similarity_search("", k=1, filter={"source_hash": source_hash})
            return len(results) > 0
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _parsed_to_lc_docs(parsed: ParsedDocument) -> list[Any]:
        """Convert ParsedDocument to LangChain Documents."""
        from langchain_core.documents import Document as LCDocument

        if parsed.pages:
            return [
                LCDocument(
                    page_content=page.text,
                    metadata={
                        "source": parsed.source,
                        "page": page.page_number,
                        "source_type": "parsed",
                    },
                )
                for page in parsed.pages
                if page.text.strip()
            ]
        return [
            LCDocument(
                page_content=parsed.text,
                metadata={"source": parsed.source, "source_type": "parsed"},
            )
        ]

    @staticmethod
    def _extractions_to_lc_docs(
        extractions: list[ExtractionResult], source: str
    ) -> list[Any]:
        """Convert ExtractionResults to LangChain Documents."""
        from langchain_core.documents import Document as LCDocument

        return [
            LCDocument(
                page_content=f"{ext.entity_class}: {ext.text}",
                metadata={
                    "source": source,
                    "source_type": "extraction",
                    "entity_class": ext.entity_class,
                    **ext.attributes,
                },
            )
            for ext in extractions
        ]

    @staticmethod
    def _create_embeddings(config: IngestionConfig) -> Any:
        """Create LangChain embeddings based on provider config."""
        if config.embedding_provider not in EMBEDDING_PROVIDERS:
            raise ConfigurationError(
                f"Unknown embedding provider: '{config.embedding_provider}'. "
                f"Available: {list(EMBEDDING_PROVIDERS.keys())}"
            )

        module_name, class_name, param_map = EMBEDDING_PROVIDERS[config.embedding_provider]

        try:
            import importlib

            module = importlib.import_module(module_name)
            embeddings_cls = getattr(module, class_name)
        except ImportError as err:
            raise ConfigurationError(
                f"Embedding provider '{config.embedding_provider}' requires '{module_name}'. "
                f"Install with: pip install {module_name}"
            ) from err

        kwargs = {}
        for param_key, config_key in param_map.items():
            kwargs[param_key] = getattr(config, f"embedding_{config_key}")

        return embeddings_cls(**kwargs)

    @staticmethod
    def _create_splitter(config: IngestionConfig) -> Any:
        """Create LangChain text splitter."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        return RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
