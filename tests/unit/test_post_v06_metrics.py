"""Tests for preset/plugin Prometheus metrics."""

from __future__ import annotations

from docpipe.observability import metrics


def test_record_preset_usage_noop_when_unavailable(monkeypatch):
    monkeypatch.setattr(metrics, "PRESET_USAGE", None)
    metrics.record_preset_usage("balanced", "ingest")


def test_record_plugin_denied_noop_when_unavailable(monkeypatch):
    monkeypatch.setattr(metrics, "PLUGIN_DENIED", None)
    metrics.record_plugin_denied("parsers", "mineru")


def test_record_preset_usage_increments_counter():
    if not metrics.metrics_available():
        return
    before = metrics.PRESET_USAGE.labels(preset="balanced", endpoint="ingest")._value.get()  # noqa: SLF001
    metrics.record_preset_usage("balanced", "ingest")
    after = metrics.PRESET_USAGE.labels(preset="balanced", endpoint="ingest")._value.get()  # noqa: SLF001
    assert after >= before + 1
