"""Built-in availability reflects installed extras without importing plugins."""

from __future__ import annotations

import importlib.util

import pytest

from docpipe.plugins.catalog import PluginCatalogBuilder
from docpipe.plugins.descriptors import PluginCategory
from docpipe.plugins.discovery import builtin_registrations
from docpipe.plugins.errors import PluginDependencyError
from docpipe.plugins.loader import PluginLoader
from docpipe.plugins.policy import PluginPolicy


def should_keep_missing_builtin_extras_visible_with_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual_find = importlib.util.find_spec

    def find_spec(name: str):
        if name in {"qdrant_client", "boto3"}:
            return None
        return actual_find(name)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)
    registrations = builtin_registrations()
    by_name = {(item.category, item.name): item for item in registrations}
    qdrant = by_name[(PluginCategory.VECTORSTORE, "qdrant")]
    s3 = by_name[(PluginCategory.SOURCE, "s3")]
    assert not qdrant.descriptor.available
    assert not s3.descriptor.available
    assert by_name[(PluginCategory.SOURCE, "local")].descriptor.available

    builder = PluginCatalogBuilder()
    for item in registrations:
        builder.add(item)
    loader = PluginLoader(builder.build(), process_policy=PluginPolicy.create())
    with pytest.raises(PluginDependencyError) as failure:
        loader.load(PluginCategory.SOURCE, "s3")
    assert failure.value.hint == "Install docpipe-sdk[s3]"
