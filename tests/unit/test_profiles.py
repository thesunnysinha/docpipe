"""Tests for install profiles, presets, and guardrails."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docpipe.chunkers.recursive_chunker import RecursiveChunker
from docpipe.config import get_settings
from docpipe.profiles.guardrails import build_plugins_payload, is_plugin_allowed
from docpipe.profiles.presets import apply_defaults_and_preset, list_runtime_presets
from docpipe.profiles.resolve import resolve_recommendation
from docpipe.registry.registry import PluginRegistry
from docpipe.server.app import create_app
from tests.conftest import MockParser


def test_runtime_presets_list():
    presets = list_runtime_presets()
    assert "balanced" in presets
    assert "description" in presets["fast"]


def test_apply_defaults_and_preset_balanced():
    settings = get_settings()
    resolved = apply_defaults_and_preset(
        {},
        preset="balanced",
        applicable={"parser", "tier", "chunker", "reranker"},
    )
    assert resolved["parser"] == "auto"
    assert resolved["tier"] == "balanced"
    assert resolved["chunker"] == "semchunk"
    assert resolved["reranker"] == "flashrank"
    assert settings.default_parser == "auto"


def test_explicit_field_wins_over_preset():
    resolved = apply_defaults_and_preset(
        {"chunker": "recursive"},
        preset="balanced",
        applicable={"chunker"},
        explicit={"chunker"},
    )
    assert resolved["chunker"] == "recursive"


def test_disabled_plugin_blocked(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOCPIPE_DISABLED_PLUGINS", "markitdown")
    registry = PluginRegistry.get()
    registry.register_parser("markitdown", MockParser)
    assert is_plugin_allowed("parsers", "markitdown") is False


def test_plugins_payload_includes_tier_and_allowed():
    registry = PluginRegistry.get()
    registry.register_parser("mock", MockParser)
    payload = build_plugins_payload()
    assert "tier" in payload["parsers"]["mock"]
    assert "allowed" in payload["parsers"]["mock"]


def test_resolve_recommendation_with_mock_parser():
    registry = PluginRegistry.get()
    registry.register_parser("markitdown", MockParser)
    registry.register_chunker("recursive", RecursiveChunker)
    result = resolve_recommendation(source="file.pdf", preset="fast")
    assert result["recommended"]["parser"] == "markitdown"


def test_profiles_endpoint():
    client = TestClient(create_app())
    response = client.get("/profiles")
    assert response.status_code == 200
    body = response.json()
    assert "runtime_presets" in body
    assert "install_profiles" in body


def test_plugins_resolve_endpoint():
    registry = PluginRegistry.get()
    registry.register_parser("markitdown", MockParser)
    client = TestClient(create_app())
    response = client.post(
        "/plugins/resolve",
        json={"source": "report.pdf", "goal": "ingest", "preset": "fast"},
    )
    assert response.status_code == 200
    assert "recommended" in response.json()
