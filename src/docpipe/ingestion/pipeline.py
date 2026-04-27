"""Ingestion pipeline: chunk, embed, and store in user's vector DB."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
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

# Tuple: (module, class, param_map, api_key_kwarg | None)
# param_map maps constructor kwarg → config attribute suffix (embedding_{suffix})
# api_key_kwarg is the constructor kwarg name for the API key, or None if not applicable
EMBEDDING_PROVIDERS = {
    "openai": ("langchain_openai", "OpenAIEmbeddings", {"model": "model"}, "openai_api_key"),
    "google": ("langchain_google_genai", "GoogleGenerativeAIEmbeddings", {"model": "model"}, "google_api_key"),
    "ollama": ("langchain_ollama", "OllamaEmbeddings", {"model": "model"}, None),
    "huggingface": ("langchain_huggingface", "HuggingFaceEmbeddings", {"model_name": "model"}, None),
}

LLM_PROVIDERS: dict[str, tuple[str, str]] = {
    "openai": ("langchain_openai", "ChatOpenAI"),
    "google": ("langchain_google_genai", "ChatGoogleGenerativeAI"),
    "ollama": ("langchain_ollama", "ChatOllama"),
    "anthropic": ("langchain_anthropic", "ChatAnthropic"),
}

CONTEXTUAL_INJECTION_PROMPT = """\
Document:
{full_text}

Chunk:
{chunk_text}

Write a 1-2 sentence context that situates this chunk within the full document. \
Be specific about what section or topic this chunk covers. Reply with only the context sentences."""

CHUNK_METHOD_SETTINGS: dict[str, dict[str, Any]] = {
    "paper": {
        "separators": ["\n## ", "\n### ", "\n\n", "\n", " "],
        "chunk_size": 1500,
        "chunk_overlap": 150,
    },
    "laws": {
        "separators": ["\nSection ", "\nArticle ", "\n\n", "\n"],
        "chunk_size": 2000,
        "chunk_overlap": 100,
    },
    "book": {
        "separators": ["\nChapter ", "\n\n", "\n"],
        "chunk_size": 2000,
        "chunk_overlap": 200,
    },
    "qa": {
        "separators": ["\nQ:", "\n\n", "\n"],
        "chunk_size": 500,
        "chunk_overlap": 50,
    },
    "manual": {
        "separators": ["\n# ", "\n## ", "\n\n", "\n"],
        "chunk_size": 800,
        "chunk_overlap": 100,
    },
    "table": {
        "separators": ["\n\n", "\n"],
        "chunk_size": 500,
        "chunk_overlap": 0,
    },
    "presentation": {
        "separators": ["\n---", "\n\n", "\n"],
        "chunk_size": 600,
        "chunk_overlap": 50,
    },
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

        # Contextual chunk injection
        if self._config.contextual_injection:
            full_text = parsed.text
            context_llm = self._create_context_llm(self._config)
            chunks = self._inject_context(chunks, full_text, context_llm)

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

    def search(
        self, query: str, top_k: int = 10, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Similarity search against the user's vector DB."""
        try:
            from langchain_postgres import PGVector

            vectorstore = PGVector(
                embeddings=self._embeddings,
                collection_name=self._config.table_name,
                connection=self._config.connection_string,
            )
            results = vectorstore.similarity_search_with_score(
                query, k=top_k, filter=filters or None
            )
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

        module_name, class_name, param_map, api_key_kwarg = EMBEDDING_PROVIDERS[config.embedding_provider]

        try:
            module = importlib.import_module(module_name)
            embeddings_cls = getattr(module, class_name)
        except ImportError as err:
            raise ConfigurationError(
                f"Embedding provider '{config.embedding_provider}' requires '{module_name}'. "
                f"Install with: pip install {module_name}"
            ) from err

        kwargs: dict[str, Any] = {}
        for param_key, config_key in param_map.items():
            kwargs[param_key] = getattr(config, f"embedding_{config_key}")

        if api_key_kwarg and config.embedding_api_key:
            kwargs[api_key_kwarg] = config.embedding_api_key

        return embeddings_cls(**kwargs)

    @staticmethod
    def _create_splitter(config: IngestionConfig) -> Any:
        """Create LangChain text splitter based on chunk_method."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        if config.chunk_method == "default" or config.chunk_method not in CHUNK_METHOD_SETTINGS:
            return RecursiveCharacterTextSplitter(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
            )

        settings = CHUNK_METHOD_SETTINGS[config.chunk_method]
        return RecursiveCharacterTextSplitter(
            separators=settings["separators"],
            chunk_size=settings["chunk_size"],
            chunk_overlap=settings["chunk_overlap"],
        )

    @staticmethod
    def _create_context_llm(config: IngestionConfig) -> Any:
        """Create LLM for contextual chunk injection."""
        if config.contextual_llm_provider not in LLM_PROVIDERS:
            raise ConfigurationError(
                f"Unknown LLM provider: '{config.contextual_llm_provider}'. "
                f"Available: {list(LLM_PROVIDERS)}"
            )
        module_name, class_name = LLM_PROVIDERS[config.contextual_llm_provider]
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except ImportError as err:
            raise ConfigurationError(
                f"LLM provider '{config.contextual_llm_provider}' requires '{module_name}'. "
                f"Install with: pip install {module_name}"
            ) from err
        return cls(model=config.contextual_llm_model)

    @staticmethod
    def _inject_context(chunks: list[Any], full_text: str, llm: Any) -> list[Any]:
        """Prepend LLM-generated situational context to each chunk."""
        from langchain_core.messages import HumanMessage

        for chunk in chunks:
            prompt = CONTEXTUAL_INJECTION_PROMPT.format(
                full_text=full_text[:4000],  # truncate to avoid token limits
                chunk_text=chunk.page_content,
            )
            try:
                context_sentence = llm.invoke([HumanMessage(content=prompt)]).content.strip()
                chunk.page_content = f"{context_sentence}\n\n{chunk.page_content}"
            except Exception as e:  # noqa: BLE001
                logger.warning("Contextual injection failed for chunk: %s", e)
        return chunks
