"""Tests for cronwatcher.scheduler."""

from datetime import datetime, timezone

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import JobState, Scheduler


@pytest.fixture()
def every_minute_job() -> JobConfig:
    return JobConfig(name="heartbeat", schedule="* * * * *", command="echo ok")


@pytest.fixture()
def scheduler(every_minute_job: JobConfig) -> Scheduler:
    s = Scheduler()
    s.register(every_minute_job)
    return s


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def test_register_adds_state(every_minute_job: JobConfig) -> None:
    s = Scheduler()
    s.register(every_minute_job)
    assert "heartbeat" in s.jobs
    assert isinstance(s.jobs["heartbeat"], JobState)


def test_record_execution_updates_last_seen(scheduler: Scheduler) -> None:
    ts = _ts("2024-01-01T12:00:00")
    scheduler.record_execution("heartbeat", executed_at=ts)
    assert scheduler.jobs["heartbeat"].last_seen == ts


def test_record_execution_resets_missed_count(scheduler: Scheduler) -> None:
    scheduler.jobs["heartbeat"].missed_count = 3
    scheduler.record_execution("heartbeat")
    assert scheduler.jobs["heartbeat"].missed_count == 0


def test_record_execution_unknown_job(scheduler: Scheduler) -> None:
    with pytest.raises(KeyError, match="unknown"):
        scheduler.record_execution("unknown")


def test_check_missed_detects_missed_job(scheduler: Scheduler) -> None:
    # No execution recorded; check at a time when the job should have run
    now = _ts("2024-01-01T12:05:30")
    missed = scheduler.check_missed(now=now)
    assert "heartbeat" in missed
    assert scheduler.jobs["heartbeat"].missed_count == 1


def test_check_missed_no_miss_after_execution(scheduler: Scheduler) -> None:
    # Record execution just before the expected fire time
    now = _ts("2024-01-01T12:05:30")
    # The most recent expected fire is 12:05:00; record execution at 12:05:10
    scheduler.record_execution("heartbeat", executed_at=_ts("2024-01-01T12:05:10"))
    missed = scheduler.check_missed(now=now)
    assert "heartbeat" not in missed


def test_check_missed_same_interval_not_double_counted(scheduler: Scheduler) -> None:
    now = _ts("2024-01-01T12:05:30")
    first = scheduler.check_missed(now=now)
    second = scheduler.check_missed(now=now)
    assert "heartbeat" in first
    # Second call in same interval must not re-report
    assert "heartbeat" not in second
    assert scheduler.jobs["heartbeat"].missed_count == 1


def test_multiple_jobs_independent(every_minute_job: JobConfig) -> None:
    job2 = JobConfig(name="backup", schedule="0 * * * *", command="backup.sh")
    s = Scheduler()
    s.register(every_minute_job)
    s.register(job2)

    now = _ts("2024-01-01T12:05:30")
    # Record heartbeat as executed; backup not executed
    s.record_execution("heartbeat", executed_at=_ts("2024-01-01T12:05:10"))
    missed = s.check_missed(now=now)

    assert "heartbeat" not in missed
    assert "backup" in missed
