"""Scoped references and resolvers for plugin credentials."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from docpipe.plugins.errors import PluginConfigurationError


class SecretReference(BaseModel):
    """Reference to a secret held outside plugin configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["environment"] = Field(...)
    name: str = Field(min_length=1, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")


class CredentialResolver(Protocol):
    """Resolve a secret reference at an explicit composition boundary."""

    def resolve(self, reference: SecretReference) -> SecretStr:
        """Return a masked secret value or raise a safe configuration error."""
        ...


class EnvironmentCredentialResolver:
    """Resolve secret references from an injected environment mapping."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def resolve(self, reference: SecretReference) -> SecretStr:
        """Resolve a secret without exposing it in an error on failure."""
        value = self._values.get(reference.name)
        if value is None:
            raise PluginConfigurationError(
                f"secret reference {reference.name!r} was not found",
                hint="Set the referenced environment variable before starting Docpipe.",
                context={"kind": reference.kind, "name": reference.name},
            )
        return SecretStr(value)
