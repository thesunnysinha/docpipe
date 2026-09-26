"""Reusable fake vector-health boundaries for API and probe specs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from docpipe.plugins.contracts.vectorstore import VectorCapability, VectorStoreBinding


@dataclass
class Probe:
    """Configurable asynchronous probe behavior."""

    result: bool = True
    wait: bool = False

    async def health(self) -> bool:
        """Return a health result or intentionally outwait a short deadline."""
        if self.wait:
            await asyncio.sleep(1)
        return self.result


class FakePlugin:
    """Expose only the health facet for probe tests."""

    def __init__(self, probe: Probe) -> None:
        self.binding = VectorStoreBinding(
            capabilities=frozenset({VectorCapability.HEALTH}), health=probe
        )


class FakeLoaded:
    """Factory wrapper mirroring a selected catalog registration."""

    def __init__(self, probe: Probe) -> None:
        self.probe = probe

    def create(self, config: Any, *, context: Any) -> FakePlugin:
        """Build a fake plugin after validating selected provider identity."""
        assert config.provider == "mock-vectors"
        return FakePlugin(self.probe)
