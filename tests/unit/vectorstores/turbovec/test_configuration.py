"""Tests for safe TurboVec filesystem configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from docpipe.plugins.contracts.vectorstore import CollectionRef
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig


def test_configuration_normalizes_root_and_validates_bit_width(tmp_path: Path) -> None:
    config = TurboVecConfig(index_root=tmp_path / "indices", bit_width=3)

    assert config.index_root.is_absolute()
    assert config.collection_path(CollectionRef("documents")).parent == config.index_root
    with pytest.raises(ValidationError):
        TurboVecConfig(index_root=tmp_path, bit_width=8)


def test_collection_path_cannot_escape_root(tmp_path: Path) -> None:
    config = TurboVecConfig(index_root=tmp_path)

    with pytest.raises(ValueError, match="collection"):
        config.collection_path(CollectionRef("../outside"))
