"""LangChain adapter for structured data extraction using with_structured_output."""

from __future__ import annotations

import logging
from typing import Any

from docpipe.core.errors import ConfigurationError, ExtractionError
from docpipe.core.types import ExtractionResult, ExtractionSchema

logger = logging.getLogger(__name__)

PROVIDER_MAP = {
    "openai": ("langchain_openai", "ChatOpenAI"),
    "google": ("langchain_google_genai", "ChatGoogleGenerativeAI"),
    "ollama": ("langchain_ollama", "ChatOllama"),
    "anthropic": ("langchain_anthropic", "ChatAnthropic"),
}


class LangChainExtractor:
    """Structured data extractor using LangChain's with_structured_output."""

    name: str = "langchain"

    def __init__(
        self,
        provider: str = "openai",
        model_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._provider = provider
        self._model_id = model_id
        self._model_kwargs = kwargs
        self._model: Any = None

    def _get_model(self, model_id: str) -> Any:
        """Lazily create the LangChain chat model."""
        if self._model is not None and self._model_id == model_id:
            return self._model

        if self._provider not in PROVIDER_MAP:
            raise ConfigurationError(
                f"Unknown LLM provider: '{self._provider}'. "
                f"Available: {list(PROVIDER_MAP.keys())}"
            )

        module_name, class_name = PROVIDER_MAP[self._provider]
        try:
            import importlib

            module = importlib.import_module(module_name)
            model_cls = getattr(module, class_name)
        except ImportError as err:
            raise ConfigurationError(
                f"Provider '{self._provider}' requires package '{module_name}'. "
                f"Install with: pip install {module_name}"
            ) from err

        self._model = model_cls(model=model_id, **self._model_kwargs)
        self._model_id = model_id
        return self._model

    def extract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: Any,
    ) -> list[ExtractionResult]:
        """Extract structured data using LangChain's with_structured_output."""
        if schema.output_model is None:
            raise ConfigurationError(
                "LangChain extractor requires schema.output_model (a Pydantic model class). "
                "Set it to define the structure of extracted data."
            )

        model = self._get_model(schema.model_id)
        structured = model.with_structured_output(schema.output_model)

        prompt = f"{schema.description}\n\nText:\n{text}"
        try:
            result = structured.invoke(prompt)
        except Exception as e:
            raise ExtractionError(f"LangChain extraction failed: {e}") from e

        return self._to_extraction_results(result)

    async def aextract(
        self,
        text: str,
        schema: ExtractionSchema,
        **kwargs: Any,
    ) -> list[ExtractionResult]:
        """Async extraction using LangChain's async invoke."""
        if schema.output_model is None:
            raise ConfigurationError(
                "LangChain extractor requires schema.output_model (a Pydantic model class)."
            )

        model = self._get_model(schema.model_id)
        structured = model.with_structured_output(schema.output_model)

        prompt = f"{schema.description}\n\nText:\n{text}"
        try:
            result = await structured.ainvoke(prompt)
        except Exception as e:
            raise ExtractionError(f"LangChain async extraction failed: {e}") from e

        return self._to_extraction_results(result)

    @classmethod
    def is_available(cls) -> bool:
        """Check if langchain-core is installed."""
        try:
            import langchain_core  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def _to_extraction_results(result: Any) -> list[ExtractionResult]:
        """Convert a Pydantic model result to ExtractionResult list."""
        from pydantic import BaseModel

        if isinstance(result, BaseModel):
            results: list[ExtractionResult] = []
            for field_name, value in result.model_dump().items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            results.append(
                                ExtractionResult(
                                    entity_class=field_name,
                                    text=str(item.get("text", item)),
                                    attributes=item,
                                )
                            )
                        else:
                            results.append(
                                ExtractionResult(
                                    entity_class=field_name,
                                    text=str(item),
                                )
                            )
                else:
                    results.append(
                        ExtractionResult(
                            entity_class=field_name,
                            text=str(value),
                            attributes={"value": value},
                        )
                    )
            return results
        elif isinstance(result, dict):
            return [
                ExtractionResult(
                    entity_class=k,
                    text=str(v),
                    attributes={"value": v},
                )
                for k, v in result.items()
            ]
        return [ExtractionResult(entity_class="result", text=str(result))]
