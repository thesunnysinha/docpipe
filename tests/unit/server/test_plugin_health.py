"""Selected-plugin probes are explicit, bounded, and safely reported."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from tests.unit.server.probe_support import FakeLoaded, Probe

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.plugin_options import VectorStoreOptions
from docpipe.config.settings import DocpipeSettings
from docpipe.schemas.health import DependencyStatus
from docpipe.server.app import create_app
from docpipe.server.plugin_health import probe_selected_vector


@pytest.mark.asyncio
async def test_explicit_probe_only_loads_selected_provider_and_has_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = DocpipeSettings(
        vector_store=VectorStoreOptions(provider="mock-vectors", options={"collection": "docs"})
    )
    runtime = build_runtime(settings)
    loaded: list[str] = []

    def load(category: Any, name: str) -> FakeLoaded:
        loaded.append(name)
        return FakeLoaded(Probe(wait=True))

    monkeypatch.setattr(runtime, "load_plugin", load)

    async with runtime:
        status = await probe_selected_vector(runtime, timeout_seconds=0.01)

    assert loaded == ["mock-vectors"]
    assert status.status == "unavailable"
    assert status.detail == "vector plugin probe timed out"


def test_default_health_does_not_load_optional_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(
        DocpipeSettings(
            auth_enabled=False,
            health_check_db=False,
            vector_store=VectorStoreOptions(
                provider="mock-vectors", options={"collection": "docs"}
            ),
        )
    )
    loaded: list[str] = []
    monkeypatch.setattr(
        app.state.docpipe_runtime,
        "load_plugin",
        lambda category, name: loaded.append(name),
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert loaded == []


def test_explicit_health_endpoint_returns_safe_probe_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(DocpipeSettings(auth_enabled=False, health_check_db=False))
    probe = AsyncMock(return_value=DependencyStatus(name="vectorstore:pgvector", status="degraded"))
    monkeypatch.setattr("docpipe.server.routers.meta.probe_selected_vector", probe)

    with TestClient(app) as client:
        response = client.get("/plugins/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    probe.assert_awaited_once()


@pytest.mark.asyncio
async def test_plugin_probe_redacts_raw_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = DocpipeSettings(
        vector_store=VectorStoreOptions(provider="mock-vectors", options={"collection": "docs"})
    )
    runtime = build_runtime(settings)

    def fail(category: Any, name: str) -> FakeLoaded:
        raise RuntimeError("secret-password in vendor message")

    monkeypatch.setattr(runtime, "load_plugin", fail)

    async with runtime:
        status = await probe_selected_vector(runtime)

    assert status.status == "unavailable"
    assert "secret-password" not in status.model_dump_json()
