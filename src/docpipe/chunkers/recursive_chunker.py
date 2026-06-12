"""Recursive character chunker (LangChain default)."""

from __future__ import annotations

import asyncio
from typing import Any

from docpipe.chunkers.settings import CHUNK_METHOD_SETTINGS
from docpipe.core.types import IngestionConfig


class RecursiveChunker:
    """LangChain RecursiveCharacterTextSplitter wrapper."""

    name = "recursive"
    license = "MIT"
    requires_gpu = False

    def __init__(self, config: IngestionConfig, **kwargs: Any) -> None:
        self._config = config
        self._splitter = self._build_splitter(config)

    @staticmethod
    def _build_splitter(config: IngestionConfig) -> Any:
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

    def split_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        return self._splitter.split_documents(documents)

    async def asplit_documents(self, documents: list[Any], **kwargs: Any) -> list[Any]:
        return await asyncio.to_thread(self.split_documents, documents, **kwargs)

    @classmethod
    def is_available(cls) -> bool:
        try:
            import langchain_text_splitters  # noqa: F401

            return True
        except ImportError:
            return False
