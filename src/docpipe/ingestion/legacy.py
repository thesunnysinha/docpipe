"""Compatibility adapters that isolate remaining LangChain ingestion objects."""

from __future__ import annotations

import hashlib
import importlib
import logging
from typing import Protocol, cast

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.core.errors import ConfigurationError
from docpipe.core.types import ExtractionResult, IngestionConfig, ParsedDocument
from docpipe.ingestion.configuration import IngestMode
from docpipe.ingestion.document_builder import DocumentBuilder, IngestionDocument

_LOGGER = logging.getLogger(__name__)
_PARENT_ID = "_docpipe_parent_id"
_SOURCE_ID = "_docpipe_source_id"

EMBEDDING_PROVIDERS = {
    "openai": ("langchain_openai", "OpenAIEmbeddings", {"model": "model"}, "openai_api_key"),
    "google": (
        "langchain_google_genai",
        "GoogleGenerativeAIEmbeddings",
        {"model": "model"},
        "google_api_key",
    ),
    "ollama": ("langchain_ollama", "OllamaEmbeddings", {"model": "model"}, None),
    "huggingface": (
        "langchain_huggingface",
        "HuggingFaceEmbeddings",
        {"model_name": "model"},
        None,
    ),
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


class LegacyChunker(Protocol):
    """Structural surface of existing registry chunkers."""

    def split_documents(self, documents: list[object]) -> list[object]:
        """Split LangChain-compatible documents."""
        ...


class LegacyDocument(Protocol):
    """Structural surface returned by LangChain text splitters."""

    page_content: str
    metadata: dict[str, object]


class LegacyLlm(Protocol):
    """Structural surface used for contextual generation."""

    def invoke(self, messages: list[object]) -> object:
        """Invoke the configured chat model."""
        ...


class KeywordConstructor(Protocol):
    """Dynamically imported provider constructor accepting named options."""

    def __call__(self, **kwargs: object) -> object:
        """Construct a provider object."""
        ...


class LangChainChunkerAdapter:
    """Convert Docpipe documents only at the legacy chunker boundary."""

    def __init__(
        self,
        chunker: LegacyChunker,
        blocking_runner: BoundedBlockingRunner,
    ) -> None:
        self._chunker = chunker
        self._runner = blocking_runner

    async def split(
        self,
        documents: tuple[IngestionDocument, ...],
    ) -> tuple[IngestionDocument, ...]:
        """Split documents and immediately normalize results back to Docpipe."""
        legacy_documents = documents_to_langchain(documents, include_internal_ids=True)
        chunks = await self._runner.run(self._chunker.split_documents, legacy_documents)
        normalized: list[IngestionDocument] = []
        for ordinal, value in enumerate(chunks):
            chunk = cast(LegacyDocument, value)
            metadata = dict(chunk.metadata)
            parent_id = metadata.pop(_PARENT_ID, "")
            source_id = metadata.pop(_SOURCE_ID, "")
            if not isinstance(parent_id, str) or not isinstance(source_id, str):
                raise TypeError("legacy chunker returned invalid Docpipe identity metadata")
            normalized.append(
                IngestionDocument(
                    record_id=_chunk_id(parent_id, ordinal, chunk.page_content),
                    text=chunk.page_content,
                    metadata=metadata,
                    source_id=source_id,
                )
            )
        return tuple(normalized)


class LangChainContextGenerator:
    """Invoke an existing synchronous chat model through bounded execution."""

    def __init__(self, llm: LegacyLlm, blocking_runner: BoundedBlockingRunner) -> None:
        self._llm = llm
        self._runner = blocking_runner

    async def generate(self, full_text: str, chunk_text: str) -> str:
        """Generate one context sentence without leaking framework messages."""
        return await self._runner.run(self._generate, full_text, chunk_text)

    def _generate(self, full_text: str, chunk_text: str) -> str:
        from langchain_core.messages import HumanMessage

        prompt = CONTEXTUAL_INJECTION_PROMPT.format(
            full_text=full_text,
            chunk_text=chunk_text,
        )
        response = self._llm.invoke([HumanMessage(content=prompt)])
        content = getattr(response, "content", None)
        if not isinstance(content, str):
            raise TypeError("context model returned non-text content")
        return content


def create_embeddings(config: IngestionConfig) -> object:
    """Construct the configured legacy embedding implementation lazily."""
    provider_entry = EMBEDDING_PROVIDERS.get(config.embedding_provider)
    if provider_entry is None:
        raise ConfigurationError(
            f"Unknown embedding provider: '{config.embedding_provider}'. "
            f"Available: {list(EMBEDDING_PROVIDERS)}"
        )
    module_name, class_name, parameter_map, api_key_keyword = provider_entry
    try:
        module = importlib.import_module(module_name)
        embeddings_class = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        raise ConfigurationError(
            f"Embedding provider '{config.embedding_provider}' requires '{module_name}'. "
            f"Install with: pip install {module_name}"
        ) from exc
    kwargs: dict[str, object] = {
        parameter: getattr(config, f"embedding_{suffix}")
        for parameter, suffix in parameter_map.items()
    }
    if api_key_keyword and config.embedding_api_key:
        kwargs[api_key_keyword] = config.embedding_api_key
    constructor = cast(KeywordConstructor, embeddings_class)
    return constructor(**kwargs)


def create_chunker(config: IngestionConfig) -> object:
    """Construct the selected legacy chunker from the compatibility registry."""
    from docpipe.registry.registry import PluginRegistry

    return PluginRegistry.get().get_chunker(config.chunker or "recursive", config=config)


def create_context_llm(config: IngestionConfig) -> object:
    """Construct the configured legacy contextual chat model lazily."""
    provider_entry = LLM_PROVIDERS.get(config.contextual_llm_provider)
    if provider_entry is None:
        raise ConfigurationError(
            f"Unknown LLM provider: '{config.contextual_llm_provider}'. "
            f"Available: {list(LLM_PROVIDERS)}"
        )
    module_name, class_name = provider_entry
    try:
        module = importlib.import_module(module_name)
        model_class = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        raise ConfigurationError(
            f"LLM provider '{config.contextual_llm_provider}' requires '{module_name}'. "
            f"Install with: pip install {module_name}"
        ) from exc
    constructor = cast(KeywordConstructor, model_class)
    return constructor(model=config.contextual_llm_model)


def documents_to_langchain(
    documents: tuple[IngestionDocument, ...],
    *,
    include_internal_ids: bool = False,
) -> list[object]:
    """Convert only at a legacy API boundary, never at vector storage."""
    from langchain_core.documents import Document

    converted: list[object] = []
    for document in documents:
        metadata: dict[str, object] = dict(document.metadata)
        if include_internal_ids:
            metadata[_PARENT_ID] = document.record_id
            metadata[_SOURCE_ID] = document.source_id
        converted.append(Document(page_content=document.text, metadata=metadata))
    return converted


def parsed_to_langchain(parsed: ParsedDocument) -> list[object]:
    """Preserve the deprecated parsed-document conversion helper."""
    return documents_to_langchain(DocumentBuilder(IngestMode.CHUNKS).build(parsed))


def extractions_to_langchain(
    extractions: list[ExtractionResult],
    source: str,
) -> list[object]:
    """Preserve the deprecated extraction conversion helper."""
    from langchain_core.documents import Document

    return [
        Document(
            page_content=f"{extraction.entity_class}: {extraction.text}",
            metadata={
                "source": source,
                "source_type": "extraction",
                "entity_class": extraction.entity_class,
                **extraction.attributes,
            },
        )
        for extraction in extractions
    ]


def inject_context_sync(chunks: list[object], full_text: str, llm: LegacyLlm) -> list[object]:
    """Preserve the deprecated synchronous contextualization helper."""
    from langchain_core.messages import HumanMessage

    for value in chunks:
        chunk = cast(LegacyDocument, value)
        prompt = CONTEXTUAL_INJECTION_PROMPT.format(
            full_text=full_text[:4000],
            chunk_text=chunk.page_content,
        )
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            content = getattr(response, "content", None)
            if isinstance(content, str):
                chunk.page_content = f"{content.strip()}\n\n{chunk.page_content}"
        except Exception:  # noqa: BLE001 -- deprecated helper preserves fail-open behavior.
            _LOGGER.warning(
                "ingestion.contextualization.skipped",
                extra={"event": "ingestion.contextualization.skipped"},
            )
    return chunks


def _chunk_id(parent_id: str, ordinal: int, text: str) -> str:
    digest = hashlib.sha256()
    for value in (parent_id, str(ordinal), text):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
