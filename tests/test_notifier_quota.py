"""Unit tests for cronwatcher.notifier_quota."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.quota import QuotaPolicy, QuotaManager
from cronwatcher.notifier_quota import QuotaEnforcingNotifier


def _utc(offset: float = 0) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=offset
    )


def _make_notifier(max_runs: int = 2, window: int = 60):
    inner = MagicMock()
    policy = QuotaPolicy(max_runs=max_runs, window_seconds=window)
    missed_quota = QuotaManager(policy)
    failure_quota = QuotaManager(policy)
    notifier = QuotaEnforcingNotifier(inner, missed_quota, failure_quota)
    return notifier, inner


def test_missed_alert_forwarded_within_quota():
    n, inner = _make_notifier(max_runs=2)
    n.notify_missed("job_a", _utc())
    inner.notify_missed.assert_called_once_with("job_a")


def test_missed_alert_suppressed_when_quota_exhausted():
    n, inner = _make_notifier(max_runs=2)
    n.notify_missed("job_a", _utc())
    n.notify_missed("job_a", _utc())
    n.notify_missed("job_a", _utc())  # third — over quota
    assert inner.notify_missed.call_count == 2


def test_failure_alert_forwarded_within_quota():
    n, inner = _make_notifier(max_runs=3)
    n.notify_failure("job_a", 1, _utc())
    inner.notify_failure.assert_called_once_with("job_a", 1)


def test_failure_alert_suppressed_when_quota_exhausted():
    n, inner = _make_notifier(max_runs=1)
    n.notify_failure("job_a", 1, _utc())
    n.notify_failure("job_a", 2, _utc())  # over quota
    assert inner.notify_failure.call_count == 1


def test_missed_and_failure_quotas_are_independent():
    n, inner = _make_notifier(max_runs=1)
    t = _utc()
    n.notify_missed("job_a", t)   # uses missed quota
    n.notify_failure("job_a", 1, t)  # failure quota still free
    inner.notify_missed.assert_called_once()
    inner.notify_failure.assert_called_once()


def test_recover_resets_both_quotas():
    n, inner = _make_notifier(max_runs=1)
    t = _utc()
    n.notify_missed("job_a", t)
    n.notify_failure("job_a", 1, t)
    n.recover("job_a")
    n.notify_missed("job_a", t)
    n.notify_failure("job_a", 1, t)
    assert inner.notify_missed.call_count == 2
    assert inner.notify_failure.call_count == 2


def test_recover_calls_inner_recover_if_present():
    n, inner = _make_notifier()
    n.recover("job_a")
    inner.recover.assert_called_once_with("job_a")


def test_different_jobs_have_independent_quotas():
    n, inner = _make_notifier(max_runs=1)
    t = _utc()
    n.notify_missed("job_a", t)
    n.notify_missed("job_b", t)  # separate quota
    assert inner.notify_missed.call_count == 2
