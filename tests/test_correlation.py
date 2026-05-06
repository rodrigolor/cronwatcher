"""Unit tests for cronwatcher.correlation."""
from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.correlation import CorrelationDetector, CorrelationEvent, CorrelationPolicy


def _utc(offset_seconds: int = 0) -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)


def test_policy_rejects_non_positive_window() -> None:
    with pytest.raises(ValueError, match="window_seconds"):
        CorrelationPolicy(window_seconds=0)


def test_policy_rejects_min_jobs_below_two() -> None:
    with pytest.raises(ValueError, match="min_jobs"):
        CorrelationPolicy(min_jobs=1)


def test_no_event_when_only_one_job_fails() -> None:
    detector = CorrelationDetector(CorrelationPolicy(window_seconds=60, min_jobs=2))
    detector.record_failure("job_a", _utc(0))
    events = detector.detect(_utc(10))
    assert events == []


def test_event_when_two_jobs_fail_within_window() -> None:
    detector = CorrelationDetector(CorrelationPolicy(window_seconds=60, min_jobs=2))
    detector.record_failure("job_a", _utc(0))
    detector.record_failure("job_b", _utc(5))
    events = detector.detect(_utc(10))
    assert len(events) == 1
    assert set(events[0].jobs) == {"job_a", "job_b"}


def test_no_event_when_failures_outside_window() -> None:
    detector = CorrelationDetector(CorrelationPolicy(window_seconds=30, min_jobs=2))
    detector.record_failure("job_a", _utc(0))
    detector.record_failure("job_b", _utc(5))
    # advance well past the window
    events = detector.detect(_utc(120))
    assert events == []


def test_event_str_representation() -> None:
    event = CorrelationEvent(jobs=["job_b", "job_a"], detected_at=_utc(0), window_seconds=300)
    text = str(event)
    assert "job_a" in text
    assert "job_b" in text
    assert "300" in text


def test_clear_removes_job_from_correlation() -> None:
    detector = CorrelationDetector(CorrelationPolicy(window_seconds=60, min_jobs=2))
    detector.record_failure("job_a", _utc(0))
    detector.record_failure("job_b", _utc(5))
    detector.clear("job_b")
    events = detector.detect(_utc(10))
    assert events == []


def test_three_jobs_meet_min_jobs_three() -> None:
    detector = CorrelationDetector(CorrelationPolicy(window_seconds=60, min_jobs=3))
    detector.record_failure("job_a", _utc(0))
    detector.record_failure("job_b", _utc(1))
    # Only 2 jobs — should not trigger with min_jobs=3
    assert detector.detect(_utc(5)) == []
    detector.record_failure("job_c", _utc(2))
    events = detector.detect(_utc(5))
    assert len(events) == 1
    assert set(events[0].jobs) == {"job_a", "job_b", "job_c"}
