"""Tests for cronwatcher.retention module."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cronwatcher.history import HistoryStore, ExecutionRecord
from cronwatcher.retention import RetentionPolicy, RetentionManager


def _utc(**kwargs) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(**kwargs)


def _rec(job: str, age_days: float, success: bool = True) -> ExecutionRecord:
    return ExecutionRecord(
        job_name=job,
        timestamp=_utc(days=age_days),
        success=success,
        exit_code=0 if success else 1,
        message="",
    )


@pytest.fixture
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(str(tmp_path / "history"))


def test_policy_rejects_non_positive_age():
    with pytest.raises(ValueError):
        RetentionPolicy(max_age_days=0)


def test_is_expired_old_record():
    policy = RetentionPolicy(max_age_days=7)
    old = _rec("job1", age_days=10)
    assert policy.is_expired(old) is True


def test_is_expired_fresh_record():
    policy = RetentionPolicy(max_age_days=7)
    fresh = _rec("job1", age_days=3)
    assert policy.is_expired(fresh) is False


def test_prune_removes_expired_records(store: HistoryStore):
    store.record(_rec("job1", age_days=40))
    store.record(_rec("job1", age_days=2))

    policy = RetentionPolicy(max_age_days=30)
    manager = RetentionManager(store, policy)
    removed = manager.prune()

    assert removed == 1
    remaining = store.read_for_job("job1")
    assert len(remaining) == 1
    assert remaining[0].success is True


def test_prune_empty_store_returns_zero(store: HistoryStore):
    policy = RetentionPolicy(max_age_days=30)
    manager = RetentionManager(store, policy)
    assert manager.prune() == 0


def test_prune_respects_max_records_per_job(store: HistoryStore):
    for i in range(10):
        store.record(_rec("job1", age_days=i))

    policy = RetentionPolicy(max_age_days=30, max_records_per_job=3)
    manager = RetentionManager(store, policy)
    removed = manager.prune()

    assert removed == 7
    assert len(store.read_for_job("job1")) == 3


def test_prune_keeps_newest_when_capping(store: HistoryStore):
    for i in range(5):
        store.record(_rec("job1", age_days=i))

    policy = RetentionPolicy(max_age_days=30, max_records_per_job=2)
    manager = RetentionManager(store, policy)
    manager.prune()

    remaining = store.read_for_job("job1")
    assert len(remaining) == 2
    # Newest records kept (age_days 0 and 1)
    ages = sorted([(datetime.now(tz=timezone.utc) - r.timestamp).days for r in remaining])
    assert ages[0] <= 1


def test_prune_multiple_jobs_independent(store: HistoryStore):
    store.record(_rec("job_a", age_days=40))
    store.record(_rec("job_a", age_days=1))
    store.record(_rec("job_b", age_days=50))
    store.record(_rec("job_b", age_days=2))

    policy = RetentionPolicy(max_age_days=30)
    manager = RetentionManager(store, policy)
    removed = manager.prune()

    assert removed == 2
    assert len(store.read_for_job("job_a")) == 1
    assert len(store.read_for_job("job_b")) == 1
