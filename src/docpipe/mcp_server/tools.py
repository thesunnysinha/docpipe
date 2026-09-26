"""Small MCP tools that adapt existing Docpipe parsing and RAG services."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import Field

from docpipe.config.settings import DocpipeSettings
from docpipe.profiles.guardrails import reset_tenant_context, set_tenant_context
from docpipe.schemas import ParseRequest, RAGQueryRequest

if TYPE_CHECKING:
    from docpipe.server.services.documents import DocumentService
    from docpipe.server.services.rag import RAGService

logger = logging.getLogger(__name__)

_PRESETS = Literal["fast", "balanced", "quality", "agents"]


class DocpipeMCPTools:
    """Bind the core parsing and RAG services to narrow MCP operations."""

    def __init__(
        self,
        document_service: DocumentService,
        rag_service: RAGService,
        settings: DocpipeSettings,
        *,
        tenant_id: str | None = None,
    ) -> None:
        self._documents = document_service
        self._rag = rag_service
        self._settings = settings
        self._tenant_id = tenant_id

    async def parse_document(
        self,
        source: Annotated[
            str,
            Field(
                min_length=1,
                description=(
                    "Document path or URL accepted by the configured Docpipe source policy. "
                    "Private and loopback URLs remain blocked unless the operator enables them."
                ),
            ),
        ],
        parser: Annotated[
            str | None,
            Field(description="Parser plugin name; omit to use configured automatic selection."),
        ] = None,
        tier: Annotated[
            Literal["fast", "balanced", "quality"] | None,
            Field(description="Optional parser quality tier."),
        ] = None,
        preset: Annotated[
            _PRESETS | None,
            Field(description="Optional runtime preset for selecting parser defaults."),
        ] = None,
    ) -> dict[str, Any]:
        """Parse an operator-approved document source into markdown and metadata."""
        tenant_tokens = set_tenant_context(self._tenant_id, settings=self._settings)
        try:
            response = await self._documents.parse(
                ParseRequest(source=source, parser=parser, tier=tier, preset=preset)
            )
            return response.model_dump(mode="json")
        except Exception as exc:
            logger.warning(
                "mcp.tool.failed",
                extra={
                    "event": "mcp.tool.failed",
                    "tool_name": "docpipe_parse",
                    "error_type": type(exc).__name__,
                },
            )
            from fastmcp.exceptions import ToolError

            raise ToolError(
                "Document parsing failed. Check the source and server configuration."
            ) from None
        finally:
            reset_tenant_context(tenant_tokens)

    async def query_documents(
        self,
        question: Annotated[
            str,
            Field(
                min_length=1,
                description="Question to answer from the configured document index.",
            ),
        ],
        llm_provider: Annotated[
            str,
            Field(min_length=1, description="Installed language-model provider identifier."),
        ],
        llm_model: Annotated[
            str,
            Field(
                min_length=1,
                description="Language-model identifier supported by that provider.",
            ),
        ],
        embedding_provider: Annotated[
            str | None,
            Field(description="Embedding provider; defaults to the operator configuration."),
        ] = None,
        embedding_model: Annotated[
            str | None,
            Field(description="Embedding model; defaults to the operator configuration."),
        ] = None,
        strategy: Annotated[
            str | None,
            Field(description="Optional retrieval strategy override."),
        ] = None,
        preset: Annotated[
            _PRESETS | None,
            Field(description="Optional RAG runtime preset."),
        ] = None,
        top_k: Annotated[
            int,
            Field(ge=1, le=50, description="Maximum number of relevant chunks to retrieve."),
        ] = 5,
    ) -> dict[str, Any]:
        """Answer a question using RAG over the operator-configured vector index."""
        tenant_tokens = set_tenant_context(self._tenant_id, settings=self._settings)
        try:
            resolved_embedding_provider = embedding_provider or self._settings.embedding_provider
            resolved_embedding_model = embedding_model or self._settings.embedding_model
            if not resolved_embedding_provider or not resolved_embedding_model:
                from fastmcp.exceptions import ToolError

                raise ToolError(
                    "RAG is not configured: set the default embedding provider and model."
                )
            if not self._settings.db_connection_string and not self._settings.vector_store:
                from fastmcp.exceptions import ToolError

                raise ToolError("RAG is not configured: set the vector database connection.")

            request = RAGQueryRequest(
                question=question,
                connection_string=self._settings.db_connection_string,
                table_name=self._settings.db_table_name,
                vector_store=self._settings.vector_store,
                embedding_provider=resolved_embedding_provider,
                embedding_model=resolved_embedding_model,
                llm_provider=llm_provider,
                llm_model=llm_model,
                strategy=strategy,
                preset=preset,
                top_k=top_k,
                system_prompt="Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
            )
            response = await self._rag.query(request)
            return response.model_dump(mode="json", exclude_none=True)
        except Exception as exc:
            # Keep expected, deliberate tool errors intact; all internal
            # exceptions are logged by type only and mapped to a safe message.
            from fastmcp.exceptions import ToolError

            if isinstance(exc, ToolError):
                raise
            logger.warning(
                "mcp.tool.failed",
                extra={
                    "event": "mcp.tool.failed",
                    "tool_name": "docpipe_rag_query",
                    "error_type": type(exc).__name__,
                },
            )
            raise ToolError(
                "RAG query failed. Check the question and server configuration."
            ) from None
        finally:
            reset_tenant_context(tenant_tokens)
