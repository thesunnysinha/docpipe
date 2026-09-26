"""Version identifiers for the stable Docpipe plugin API."""

import re
from dataclasses import dataclass

_SEMANTIC_VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


@dataclass(frozen=True, order=True, slots=True)
class PluginApiVersion:
    """A comparable ``major.minor.patch`` Docpipe plugin API version."""

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        """Reject invalid versions constructed without :meth:`parse`."""
        components = (self.major, self.minor, self.patch)
        if any(isinstance(component, bool) or component < 0 for component in components):
            raise ValueError("semantic version components must be non-negative integers")

    @classmethod
    def parse(cls, value: str) -> "PluginApiVersion":
        """Parse a dotted semantic version string."""
        match = _SEMANTIC_VERSION.fullmatch(value)
        if match is None:
            raise ValueError(f"invalid semantic version: {value!r}")
        return cls(*(int(component) for component in match.groups()))

    def __str__(self) -> str:
        """Render the stable dotted representation."""
        return f"{self.major}.{self.minor}.{self.patch}"


DOCPIPE_PLUGIN_API_VERSION = PluginApiVersion(1, 0, 0)
