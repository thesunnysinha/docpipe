"""Optional DeepEval smoke tests (skipped without profile-eval-ci extra)."""

from __future__ import annotations

import pytest

deepeval = pytest.importorskip("deepeval")


def test_deepeval_answer_relevancy_metric_importable() -> None:
    from deepeval.metrics import AnswerRelevancyMetric

    assert AnswerRelevancyMetric.__name__ == "AnswerRelevancyMetric"
