"""Validated Qdrant connection and collection settings."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator

from docpipe.plugins.configuration import TypedPluginConfig
from docpipe.plugins.contracts.vectorstore import CollectionRef


class QdrantConfig(TypedPluginConfig):
    """Connection policy for one selected Qdrant adapter instance."""

    url: str | None = Field(
        default=None,
        description="Remote HTTP(S) endpoint; exclusive with the local in-memory location.",
    )
    location: Literal[":memory:"] | None = Field(
        default=None,
        description="Use an in-memory Qdrant instance; mutually exclusive with url.",
    )
    collection: str = Field(
        default="documents",
        description="Validated collection name used to store and query document vectors.",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="Optional credential for authenticating with the remote Qdrant service.",
    )
    timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=120,
        description="Maximum duration in seconds to wait for a Qdrant operation.",
    )
    max_scan_points: int = Field(
        default=100_000,
        ge=1,
        le=1_000_000,
        description="Upper bound on points scanned by operations that enumerate collection data.",
    )
    distance: Literal["cosine", "dot", "euclid"] = Field(
        default="cosine",
        description="Distance metric used to compare stored and query vectors.",
    )
    allow_insecure_http: bool = Field(
        default=False,
        description="Allow unencrypted remote HTTP; HTTPS is required otherwise.",
    )

    @model_validator(mode="after")
    def check_endpoint(self) -> QdrantConfig:
        """Require exactly one remote or in-memory endpoint."""
        if (self.url is None) == (self.location is None):
            raise ValueError("exactly one of url or location is required")
        if self.url is not None:
            parsed = urlsplit(self.url)
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("Qdrant URL must not contain credentials, query, or fragment")
            if not parsed.hostname or parsed.scheme not in {"https", "http"}:
                raise ValueError("Qdrant URL must use HTTP(S) and include a host")
            if parsed.scheme == "http" and not self.allow_insecure_http:
                raise ValueError("HTTP Qdrant URL requires explicit allow_insecure_http")
        return self

    @field_validator("collection")
    @classmethod
    def validate_collection(cls, value: str) -> str:
        """Keep collection names inside the shared safe-identifier policy."""
        return CollectionRef(value).name
