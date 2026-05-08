"""Tests for cronwatcher.sla."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from cronwatcher.sla import SLAPolicy, SLAViolation, SLAChecker
from cronwatcher.history import ExecutionRecord


def _utc(offset_hours: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(hours=offset_hours)


def _rec(job: str, success: bool, offset_hours: float = 0, duration: float | None = None) -> ExecutionRecord:
    return ExecutionRecord(
        job_name=job,
        success=success,
        timestamp=_utc(offset_hours),
        duration_seconds=duration,
    )


@pytest.fixture()
def store():
    s = MagicMock()
    s.read_for_job.return_value = []
    return s


# --- SLAPolicy validation ---

def test_policy_rejects_invalid_success_rate():
    with pytest.raises(ValueError, match="min_success_rate"):
        SLAPolicy(min_success_rate=1.5)


def test_policy_rejects_negative_success_rate():
    with pytest.raises(ValueError, match="min_success_rate"):
        SLAPolicy(min_success_rate=-0.1)


def test_policy_rejects_non_positive_duration():
    with pytest.raises(ValueError, match="max_duration_seconds"):
        SLAPolicy(max_duration_seconds=0)


def test_policy_rejects_non_positive_window():
    with pytest.raises(ValueError, match="window_hours"):
        SLAPolicy(window_hours=0)


def test_policy_accepts_valid_values():
    p = SLAPolicy(min_success_rate=0.9, max_duration_seconds=30.0, window_hours=12)
    assert p.min_success_rate == 0.9


# --- SLAChecker registration ---

def test_register_stores_policy(store):
    checker = SLAChecker(store)
    policy = SLAPolicy(min_success_rate=0.8)
    checker.register("backup", policy)
    assert checker.policy_for("backup") is policy


def test_register_empty_name_raises(store):
    checker = SLAChecker(store)
    with pytest.raises(ValueError):
        checker.register("", SLAPolicy())


def test_check_unknown_job_returns_empty(store):
    checker = SLAChecker(store)
    assert checker.check("unknown") == []


# --- Success rate checks ---

def test_no_violation_when_all_succeed(store):
    store.read_for_job.return_value = [
        _rec("job", True, -1),
        _rec("job", True, -2),
    ]
    checker = SLAChecker(store)
    checker.register("job", SLAPolicy(min_success_rate=1.0))
    assert checker.check("job", now=_utc()) == []


def test_violation_when_success_rate_low(store):
    store.read_for_job.return_value = [
        _rec("job", True, -1),
        _rec("job", False, -2),
        _rec("job", False, -3),
    ]
    checker = SLAChecker(store)
    checker.register("job", SLAPolicy(min_success_rate=0.9))
    violations = checker.check("job", now=_utc())
    assert len(violations) == 1
    assert violations[0].reason == "success rate below threshold"
    assert abs(violations[0].actual_value - (1 / 3)) < 1e-9


def test_records_outside_window_excluded(store):
    store.read_for_job.return_value = [
        _rec("job", False, -25),  # outside 24-hour window
        _rec("job", True, -1),
    ]
    checker = SLAChecker(store)
    checker.register("job", SLAPolicy(min_success_rate=1.0, window_hours=24))
    assert checker.check("job", now=_utc()) == []


# --- Duration checks ---

def test_violation_when_duration_exceeded(store):
    store.read_for_job.return_value = [
        _rec("job", True, -1, duration=120.0),
    ]
    checker = SLAChecker(store)
    checker.register("job", SLAPolicy(max_duration_seconds=60.0))
    violations = checker.check("job", now=_utc())
    assert any(v.reason == "max duration exceeded" for v in violations)


def test_no_duration_violation_when_within_limit(store):
    store.read_for_job.return_value = [
        _rec("job", True, -1, duration=30.0),
    ]
    checker = SLAChecker(store)
    checker.register("job", SLAPolicy(max_duration_seconds=60.0))
    assert checker.check("job", now=_utc()) == []


# --- check_all ---

def test_check_all_returns_all_jobs(store):
    store.read_for_job.return_value = []
    checker = SLAChecker(store)
    checker.register("job_a", SLAPolicy())
    checker.register("job_b", SLAPolicy())
    result = checker.check_all(now=_utc())
    assert set(result.keys()) == {"job_a", "job_b"}


# --- SLAViolation str ---

def test_violation_str_contains_job_name():
    v = SLAViolation("my_job", "success rate below threshold", 0.5, 0.9, _utc())
    assert "my_job" in str(v)
    assert "success rate" in str(v)
