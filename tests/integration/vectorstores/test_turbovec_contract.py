"""Optional conformance coverage against the installed TurboVec implementation."""

from __future__ import annotations

from pathlib import Path

import pytest

from docpipe.core.blocking import BoundedBlockingRunner
from docpipe.plugins.contracts.vectorstore import CollectionRef
from docpipe.testing.vectorstores import assert_vector_store_conformance
from docpipe.vectorstores.turbovec.adapter import TurboVecAdapter
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig
from docpipe.vectorstores.turbovec.repository import TurboVecFileRepository

pytestmark = pytest.mark.requires_turbovec


@pytest.mark.asyncio
async def test_turbovec_vector_store_contract(tmp_path: Path) -> None:
    try:
        from turbovec import IdMapIndex  # noqa: F401
    except ImportError:
        pytest.skip("TurboVec is not installed")
    config = TurboVecConfig(index_root=tmp_path)
    repository = TurboVecFileRepository(config)

    async with BoundedBlockingRunner(max_concurrency=2) as runner:
        adapter = TurboVecAdapter(config, repository, runner)
        await assert_vector_store_conformance(
            adapter.binding,
            collection=CollectionRef("contract"),
            dimensions=8,
        )
