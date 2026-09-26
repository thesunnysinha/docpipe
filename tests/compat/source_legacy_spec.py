"""Compatibility coverage while parsers move behind source resolvers."""

from __future__ import annotations

import stat
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.core.types import DocumentFormat, ParsedDocument
from docpipe.registry.registry import PluginRegistry
from docpipe.schemas import ParseRequest
from docpipe.server.app import create_app
from docpipe.server.services.documents import DocumentService


class ReadingParser:
    """Legacy path-only parser that records its unchanged string input."""

    inputs: list[str] = []

    async def aparse(self, source: str) -> ParsedDocument:
        self.inputs.append(source)
        path = Path(source)
        return ParsedDocument(
            source=source,
            format=DocumentFormat.TEXT,
            text=path.read_text(encoding="utf-8"),
        )


def _registry() -> PluginRegistry:
    ReadingParser.inputs = []
    registry = PluginRegistry.get()
    registry.register_parser("reading", ReadingParser)
    return registry


@pytest.mark.asyncio
async def test_local_path_response_and_parser_behavior_remain_compatible(
    tmp_path: Path,
) -> None:
    document = tmp_path / "report.txt"
    document.write_text("local contents", encoding="utf-8")
    settings = DocpipeSettings(source_allowed_roots=(tmp_path,))
    runtime = build_runtime(settings, legacy_registry=_registry())

    async with runtime:
        response = await DocumentService(settings, runtime.legacy_registry, runtime).parse(
            ParseRequest(source=str(document), parser="reading")
        )

    assert response.source == str(document.resolve())
    assert response.content == "local contents"
    assert ReadingParser.inputs == [str(document.resolve())]


@pytest.mark.asyncio
async def test_http_input_is_materialized_but_result_keeps_safe_http_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    downloads = tmp_path / "downloads"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"remote contents", request=request)

    monkeypatch.setattr(
        "docpipe.sources.http.pinned_async_transport",
        lambda policy: httpx.MockTransport(handler),
    )
    settings = DocpipeSettings(source_allowed_roots=(tmp_path,), source_temporary_root=downloads)
    runtime = build_runtime(settings, legacy_registry=_registry())

    async with runtime:
        response = await DocumentService(settings, runtime.legacy_registry, runtime).parse(
            ParseRequest(
                source="https://example.org/report.txt?X-Amz-Signature=private",
                parser="reading",
            )
        )

    assert response.source == "https://example.org/report.txt"
    assert response.content == "remote contents"
    assert len(ReadingParser.inputs) == 1
    assert ReadingParser.inputs[0].startswith(str(downloads))
    assert stat.S_IMODE(downloads.stat().st_mode) == 0o700
    assert list(downloads.iterdir()) == []


def test_parse_http_endpoint_preserves_response_shape(tmp_path: Path) -> None:
    document = tmp_path / "report.txt"
    document.write_text("API contents", encoding="utf-8")
    settings = DocpipeSettings(
        auth_enabled=False,
        source_allowed_roots=(tmp_path,),
    )
    app = create_app(settings)
    app.state.docpipe_runtime.legacy_registry.register_parser("reading", ReadingParser)
    PluginRegistry.get().register_parser("reading", ReadingParser)

    with TestClient(app) as client:
        response = client.post(
            "/parse",
            json={"source": str(document), "parser": "reading"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "source": str(document.resolve()),
        "format": "text",
        "content": "API contents",
        "metadata": {},
    }
