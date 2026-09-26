"""Tests for lazy TurboVec plugin construction."""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Protocol

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.configuration import PluginConfig
from docpipe.plugins.discovery import builtin_registrations
from docpipe.plugins.loader import PluginFactoryContext
from docpipe.vectorstores.turbovec.factory import create_plugin


class ImportFunction(Protocol):
    def __call__(
        self,
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object: ...


def test_discovery_and_factory_do_not_import_vendor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import: ImportFunction = builtins.__import__

    def guarded_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "turbovec":
            raise AssertionError("vendor imported during discovery or construction")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    registration = next(item for item in builtin_registrations() if item.name == "turbovec")
    runner = BoundedBlockingRunner(max_concurrency=1)
    try:
        adapter = create_plugin(
            PluginConfig(provider="turbovec", options={"index_root": str(tmp_path)}),
            context=PluginFactoryContext(blocking_runner=runner),
        )
    finally:
        runner.close()

    assert registration.import_target == "docpipe.vectorstores.turbovec.factory:create_plugin"
    assert adapter.binding.capabilities
