"""Configured plugins receive a scoped credential resolver, not raw secrets."""

from __future__ import annotations

import pytest

from docpipe.bootstrap.runtime import build_runtime
from docpipe.config.settings import DocpipeSettings
from docpipe.plugins.credentials import SecretReference


def test_runtime_injects_environment_credentials_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DOCPIPE_TEST_PLUGIN_SECRET", "private-value")
    runtime = build_runtime(DocpipeSettings())
    monkeypatch.delenv("DOCPIPE_TEST_PLUGIN_SECRET")

    resolver = runtime.factory_context().credentials

    assert resolver is not None
    secret = resolver.resolve(
        SecretReference(kind="environment", name="DOCPIPE_TEST_PLUGIN_SECRET")
    )
    assert secret.get_secret_value() == "private-value"
    assert "private-value" not in repr(runtime.factory_context())
