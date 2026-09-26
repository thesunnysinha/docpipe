"""Pure process- and tenant-level plugin policy decisions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from docpipe.plugins.catalog import PluginRegistration
from docpipe.plugins.descriptors import PluginCategory


class PolicyReason(str, Enum):
    """Stable reason for a plugin policy decision."""

    ALLOWED = "allowed"
    DENIED = "denied"
    NOT_ALLOWLISTED = "not-allowlisted"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Deterministic result of evaluating a registration."""

    allowed: bool
    reason: PolicyReason


@dataclass(frozen=True, slots=True)
class PluginPolicy:
    """Immutable allowlists and denylist applied at one policy scope."""

    allowlists: Mapping[PluginCategory, frozenset[str]]
    denylist: frozenset[str]

    @classmethod
    def create(
        cls,
        *,
        allowlists: Mapping[PluginCategory, set[str] | frozenset[str]] | None = None,
        denylist: set[str] | frozenset[str] | None = None,
    ) -> PluginPolicy:
        """Copy caller-owned collections into an immutable policy."""
        copied = {category: frozenset(names) for category, names in (allowlists or {}).items()}
        return cls(MappingProxyType(copied), frozenset(denylist or ()))


def evaluate_plugin_policy(
    registration: PluginRegistration,
    *,
    process: PluginPolicy,
    tenant: PluginPolicy | None = None,
) -> PolicyDecision:
    """Apply process policy first and optional tenant policy second.

    Tenant policy can narrow process permissions but can never grant a plugin
    rejected at the process boundary.
    """
    process_decision = _evaluate_scope(registration, process)
    if not process_decision.allowed or tenant is None:
        return process_decision
    return _evaluate_scope(registration, tenant)


def _evaluate_scope(registration: PluginRegistration, policy: PluginPolicy) -> PolicyDecision:
    if registration.name in policy.denylist:
        return PolicyDecision(False, PolicyReason.DENIED)
    allowed_names = policy.allowlists.get(registration.category)
    if allowed_names is not None and registration.name not in allowed_names:
        return PolicyDecision(False, PolicyReason.NOT_ALLOWLISTED)
    if not registration.descriptor.available:
        return PolicyDecision(False, PolicyReason.UNAVAILABLE)
    return PolicyDecision(True, PolicyReason.ALLOWED)
