"""Validated secret-safe pgvector plugin configuration."""

from __future__ import annotations

from pydantic import Field, SecretStr, field_validator

from docpipe.plugins.configuration import TypedPluginConfig
from docpipe.plugins.contracts.vectorstore import CollectionRef


class PgVectorConfig(TypedPluginConfig):
    """Immutable connection and default collection settings for pgvector."""

    dsn: SecretStr = Field(
        ...,
        description="PostgreSQL connection string, retained as a masked secret value.",
    )
    collection: str = Field(
        default="documents",
        description="Default collection name, validated with Docpipe's collection policy.",
    )
    connect_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=120,
        description="Maximum connection-establishment time in seconds, from greater than 0 to 120.",
    )

    @field_validator("collection")
    @classmethod
    def validate_collection(cls, value: str) -> str:
        """Apply the domain collection-name policy during configuration parsing."""
        return CollectionRef(value).name

    @property
    def default_collection(self) -> CollectionRef:
        """Return the validated default collection reference."""
        return CollectionRef(self.collection)

    @classmethod
    def from_legacy(cls, *, connection_string: str, table_name: str) -> PgVectorConfig:
        """Translate deprecated connection fields at the compatibility boundary."""
        return cls(dsn=SecretStr(connection_string), collection=table_name)
