"""MCP adapter tests for the existing Docpipe parsing and RAG services."""

from __future__ import annotations

import asyncio
import sys
import types
from typing import Any

import pytest

from docpipe.config.settings import DocpipeSettings
from docpipe.mcp_server.tools import DocpipeMCPTools
from docpipe.profiles.guardrails import get_tenant_context
from docpipe.schemas import ParseResponse, RAGQueryResponse


class FakeToolError(Exception):
    """Stand-in for FastMCP's client-visible safe tool exception."""


class FakeDocumentService:
    def __init__(
        self,
        response: ParseResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or ParseResponse(
            source="/safe/report.pdf",
            format="pdf",
            content="# Report",
            metadata={"pages": 1},
        )
        self.error = error
        self.request: Any = None
        self.tenant_id: str | None = None

    async def parse(self, request: Any) -> ParseResponse:
        self.tenant_id = get_tenant_context()
        self.request = request
        if self.error:
            raise self.error
        return self.response


class FakeRAGService:
    def __init__(self) -> None:
        self.request: Any = None
        self.response = RAGQueryResponse(
            query="What is the policy?",
            answer="The policy says ...",
            strategy="hybrid",
            chunks=[],
            sources=[],
            timing_seconds=0.1,
            usage=None,
        )

    async def query(self, request: Any) -> RAGQueryResponse:
        self.request = request
        return self.response


def _install_fake_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fastmcp = types.ModuleType("fastmcp")
    fastmcp.__path__ = []  # type: ignore[attr-defined]
    exceptions = types.ModuleType("fastmcp.exceptions")
    exceptions.ToolError = FakeToolError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fastmcp", fastmcp)
    monkeypatch.setitem(sys.modules, "fastmcp.exceptions", exceptions)


def test_parse_tool_reuses_document_service() -> None:
    documents = FakeDocumentService()
    tools = DocpipeMCPTools(documents, FakeRAGService(), DocpipeSettings())  # type: ignore[arg-type]

    result = asyncio.run(tools.parse_document("/safe/report.pdf", parser="markitdown"))

    assert result["content"] == "# Report"
    assert documents.request.source == "/safe/report.pdf"
    assert documents.request.parser == "markitdown"


def test_mcp_tool_binds_operator_tenant_for_service_call_and_resets_context() -> None:
    documents = FakeDocumentService()
    tools = DocpipeMCPTools(
        documents,
        FakeRAGService(),
        DocpipeSettings(),
        tenant_id="tenant-finance",
    )  # type: ignore[arg-type]

    asyncio.run(tools.parse_document("/safe/report.pdf"))

    assert documents.tenant_id == "tenant-finance"
    assert get_tenant_context() is None


def test_rag_tool_uses_operator_database_configuration() -> None:
    settings = DocpipeSettings(
        db_connection_string="postgresql://operator:secret@db/docpipe",
        db_table_name="knowledge",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        vector_backend="pgvector",
    )
    rag = FakeRAGService()
    tools = DocpipeMCPTools(FakeDocumentService(), rag, settings)  # type: ignore[arg-type]

    result = asyncio.run(
        tools.query_documents(
            question="What is the policy?",
            llm_provider="openai",
            llm_model="gpt-4.1-mini",
        )
    )

    assert result["answer"] == "The policy says ..."
    assert rag.request.connection_string == settings.db_connection_string
    assert rag.request.table_name == "knowledge"
    assert rag.request.embedding_provider == "openai"
    assert rag.request.llm_model == "gpt-4.1-mini"


def test_rag_tool_does_not_accept_client_selected_database_target() -> None:
    settings = DocpipeSettings(
        db_connection_string="postgresql://operator:secret@db/docpipe",
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
    )
    tools = DocpipeMCPTools(FakeDocumentService(), FakeRAGService(), settings)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        asyncio.run(
            tools.query_documents(
                question="query",
                llm_provider="openai",
                llm_model="gpt-4.1-mini",
                connection_string="postgresql://attacker/other-db",  # type: ignore[call-arg]
            )
        )


def test_internal_parser_failure_is_logged_without_exception_details(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _install_fake_tool_error(monkeypatch)
    documents = FakeDocumentService(error=RuntimeError("secret=do-not-log"))
    tools = DocpipeMCPTools(documents, FakeRAGService(), DocpipeSettings())  # type: ignore[arg-type]

    with pytest.raises(FakeToolError, match="Document parsing failed"):
        asyncio.run(tools.parse_document("/safe/report.pdf"))

    assert any(record.error_type == "RuntimeError" for record in caplog.records)
    assert "secret=do-not-log" not in caplog.text


def test_parse_tool_does_not_swallow_request_cancellation() -> None:
    documents = FakeDocumentService(error=asyncio.CancelledError())
    tools = DocpipeMCPTools(documents, FakeRAGService(), DocpipeSettings())  # type: ignore[arg-type]

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(tools.parse_document("/safe/report.pdf"))
