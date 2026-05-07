"""Unit tests for cronwatcher.quota."""
from datetime import datetime, timezone, timedelta

import pytest

from cronwatcher.quota import QuotaPolicy, QuotaManager


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=offset_seconds
    )


def test_policy_rejects_zero_max_runs():
    with pytest.raises(ValueError, match="max_runs"):
        QuotaPolicy(max_runs=0, window_seconds=60)


def test_policy_rejects_zero_window():
    with pytest.raises(ValueError, match="window_seconds"):
        QuotaPolicy(max_runs=3, window_seconds=0)


def test_first_run_always_allowed():
    mgr = QuotaManager(QuotaPolicy(max_runs=2, window_seconds=60))
    assert mgr.is_allowed("job_a", _utc()) is True


def test_runs_within_quota_all_allowed():
    mgr = QuotaManager(QuotaPolicy(max_runs=3, window_seconds=60))
    t = _utc()
    mgr.record_run("job_a", t)
    mgr.record_run("job_a", t)
    assert mgr.is_allowed("job_a", t) is True


def test_run_exceeding_quota_denied():
    mgr = QuotaManager(QuotaPolicy(max_runs=2, window_seconds=60))
    t = _utc()
    mgr.record_run("job_a", t)
    mgr.record_run("job_a", t)
    assert mgr.is_allowed("job_a", t) is False


def test_old_runs_evicted_after_window():
    mgr = QuotaManager(QuotaPolicy(max_runs=2, window_seconds=60))
    mgr.record_run("job_a", _utc(0))
    mgr.record_run("job_a", _utc(10))
    # Both runs are now outside the window
    assert mgr.is_allowed("job_a", _utc(70)) is True


def test_remaining_decreases_with_runs():
    mgr = QuotaManager(QuotaPolicy(max_runs=3, window_seconds=60))
    t = _utc()
    assert mgr.remaining("job_a", t) == 3
    mgr.record_run("job_a", t)
    assert mgr.remaining("job_a", t) == 2
    mgr.record_run("job_a", t)
    assert mgr.remaining("job_a", t) == 1


def test_remaining_never_negative():
    mgr = QuotaManager(QuotaPolicy(max_runs=1, window_seconds=60))
    t = _utc()
    mgr.record_run("job_a", t)
    mgr.record_run("job_a", t)  # exceeds quota
    assert mgr.remaining("job_a", t) == 0


def test_reset_clears_state():
    mgr = QuotaManager(QuotaPolicy(max_runs=1, window_seconds=60))
    t = _utc()
    mgr.record_run("job_a", t)
    assert mgr.is_allowed("job_a", t) is False
    mgr.reset("job_a")
    assert mgr.is_allowed("job_a", t) is True


def test_independent_jobs_do_not_share_quota():
    mgr = QuotaManager(QuotaPolicy(max_runs=1, window_seconds=60))
    t = _utc()
    mgr.record_run("job_a", t)
    assert mgr.is_allowed("job_b", t) is True
