"""Tests for deterministic process and tenant plugin policy."""

from __future__ import annotations

from docpipe.plugins.catalog import PluginOrigin, PluginRegistration
from docpipe.plugins.descriptors import PluginCategory, PluginDescriptor
from docpipe.plugins.policy import PluginPolicy, PolicyReason, evaluate_plugin_policy


def registration(name: str) -> PluginRegistration:
    """Build a source-plugin policy fixture."""
    return PluginRegistration(
        category=PluginCategory.SOURCE,
        name=name,
        distribution=f"docpipe-{name}",
        import_target=f"docpipe_{name}:factory",
        descriptor=PluginDescriptor(
            name=name,
            category=PluginCategory.SOURCE,
            description=f"{name} source",
        ),
        origin=PluginOrigin.THIRD_PARTY,
    )


def test_global_denylist_wins_over_category_allowlist() -> None:
    policy = PluginPolicy.create(
        allowlists={PluginCategory.SOURCE: {"http", "s3"}},
        denylist={"s3"},
    )

    decision = evaluate_plugin_policy(registration("s3"), process=policy)

    assert not decision.allowed
    assert decision.reason is PolicyReason.DENIED


def test_category_allowlist_rejects_unlisted_plugin() -> None:
    policy = PluginPolicy.create(allowlists={PluginCategory.SOURCE: {"http"}})

    decision = evaluate_plugin_policy(registration("s3"), process=policy)

    assert not decision.allowed
    assert decision.reason is PolicyReason.NOT_ALLOWLISTED


def test_tenant_policy_can_narrow_but_not_expand_process_policy() -> None:
    process = PluginPolicy.create(allowlists={PluginCategory.SOURCE: {"http"}})
    tenant = PluginPolicy.create(allowlists={PluginCategory.SOURCE: {"http", "s3"}})

    denied = evaluate_plugin_policy(registration("s3"), process=process, tenant=tenant)
    allowed = evaluate_plugin_policy(registration("http"), process=process, tenant=tenant)

    assert not denied.allowed
    assert allowed.allowed
    assert allowed.reason is PolicyReason.ALLOWED
