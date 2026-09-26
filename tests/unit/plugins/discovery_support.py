"""Static distribution and entry-point fixtures for catalog specifications."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FakeEntryPoint:
    """Minimal entry-point metadata used by discovery specs."""

    group: str
    name: str
    value: str


class FakeDistribution:
    """Distribution metadata that never imports implementation code."""

    def __init__(self, name: str, entry_points: tuple[FakeEntryPoint, ...], manifest: str | None):
        self.metadata = {"Name": name}
        self.entry_points = entry_points
        self._manifest = manifest

    def read_text(self, filename: str) -> str | None:
        """Return static plugin metadata when requested."""
        return self._manifest if filename == "docpipe-plugin.json" else None


def distribution(name: str, plugin: str, manifest: str | None) -> FakeDistribution:
    """Build one isolated vector-store distribution fixture."""
    return FakeDistribution(
        name,
        (FakeEntryPoint("docpipe.vectorstores", plugin, f"{plugin}_plugin:create_plugin"),),
        manifest,
    )
