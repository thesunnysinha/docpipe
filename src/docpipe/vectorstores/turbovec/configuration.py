"""Validated filesystem configuration for the TurboVec plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from docpipe.plugins.configuration import TypedPluginConfig
from docpipe.plugins.contracts.vectorstore import CollectionRef


class TurboVecConfig(TypedPluginConfig):
    """Immutable local-index settings with path-confinement guarantees.

    Configuration validation is side-effect free. Filesystem creation and
    permission checks happen only when a selected adapter performs an operation.
    """

    index_root: Path = Field(
        default=Path(".docpipe/indices"),
        description="Root for local TurboVec indexes; validation performs no disk writes.",
    )
    collection: str = Field(
        default="documents",
        description="Default collection name, validated using Docpipe's safe collection policy.",
    )
    bit_width: Literal[2, 3, 4] = Field(
        default=4,
        description="Bits per quantized vector value supported by the TurboVec index.",
    )
    max_dimensions: int = Field(
        default=16_384,
        ge=8,
        le=16_384,
        description="Maximum vector dimensions; an 8-byte multiple no greater than 16,384.",
    )

    @field_validator("index_root", mode="before")
    @classmethod
    def normalize_index_root(cls, value: object) -> Path:
        """Expand and resolve the configured root without touching the disk."""
        if not isinstance(value, (str, Path)):
            raise TypeError("index_root must be a filesystem path")
        return Path(value).expanduser().resolve(strict=False)

    @field_validator("collection")
    @classmethod
    def validate_collection(cls, value: str) -> str:
        """Apply Docpipe's safe collection-name policy."""
        return CollectionRef(value).name

    @field_validator("max_dimensions")
    @classmethod
    def validate_max_dimensions(cls, value: int) -> int:
        """Match TurboVec's eight-coordinate block geometry."""
        if value % 8:
            raise ValueError("max_dimensions must be a multiple of eight")
        return value

    @property
    def default_collection(self) -> CollectionRef:
        """Return the validated default collection."""
        return CollectionRef(self.collection)

    def collection_path(self, collection: CollectionRef) -> Path:
        """Resolve one collection below the configured root.

        Raises:
            ValueError: If a collection could resolve outside ``index_root``.
        """
        candidate = (self.index_root / collection.name).resolve(strict=False)
        if not candidate.is_relative_to(self.index_root):
            raise ValueError("collection path escapes the configured index root")
        return candidate

    def validate_dimensions(self, dimensions: int) -> None:
        """Validate dimensions against the selected TurboVec geometry."""
        if dimensions < 8 or dimensions > self.max_dimensions or dimensions % 8:
            raise ValueError(
                "TurboVec dimensions must be a positive multiple of eight "
                f"not exceeding {self.max_dimensions}"
            )
