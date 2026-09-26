"""Tests for SDK, server, and compatibility composition roots."""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.requests import Request

from docpipe.bootstrap.sdk import create_sdk_runtime, reset_default_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.registry.registry import PluginRegistry
from docpipe.server.app import create_app
from docpipe.server.deps import get_app_settings, get_registry, get_runtime

SOURCE_ROOT = Path(__file__).parents[3] / "src" / "docpipe"


def test_fastapi_uses_and_closes_one_application_runtime() -> None:
    app = create_app(DocpipeSettings(control_db_enabled=False, auth_enabled=False))
    runtime = app.state.docpipe_runtime

    assert not runtime.is_active
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert app.state.docpipe_runtime is runtime
        assert runtime.is_active
    assert not runtime.is_active


def test_server_dependencies_read_runtime_from_app_state() -> None:
    settings = DocpipeSettings(server_port=9123)
    app = create_app(settings)
    request = Request({"type": "http", "app": app})

    runtime = get_runtime(request)

    assert get_app_settings(runtime) is settings
    assert get_registry(runtime) is runtime.legacy_registry


def test_sdk_composition_uses_explicit_settings() -> None:
    settings = DocpipeSettings(server_port=9001)

    runtime = create_sdk_runtime(settings)

    assert runtime.settings is settings


def test_legacy_registry_get_remains_a_singleton_compatibility_facade() -> None:
    reset_default_runtime()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        first = PluginRegistry.get()
        second = PluginRegistry.get()

    assert first is second
    assert sum(item.category is DeprecationWarning for item in caught) <= 1


def test_new_bootstrap_and_coordinator_modules_do_not_read_globals() -> None:
    paths = list((SOURCE_ROOT / "bootstrap").glob("*.py"))
    paths.extend(SOURCE_ROOT.rglob("coordinator.py"))

    calls: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                is_registry_get = (
                    node.func.attr == "get"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "PluginRegistry"
                )
                if is_registry_get:
                    calls.append(f"{path.name}:{node.lineno}:{node.func.attr}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "get_settings":
                    calls.append(f"{path.name}:{node.lineno}:get_settings")

    assert calls == []
