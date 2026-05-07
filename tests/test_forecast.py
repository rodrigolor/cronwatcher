"""Tests for cronwatcher.forecast."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.forecast import Forecaster, ForecastEntry
from cronwatcher.scheduler import JobState, Scheduler


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)


@pytest.fixture()
def every_minute_job() -> JobConfig:
    return JobConfig(name="backup", cron="* * * * *", grace_seconds=60)


@pytest.fixture()
def scheduler() -> Scheduler:
    s = Scheduler()
    return s


def test_forecast_returns_entry_per_job(every_minute_job, scheduler):
    scheduler.register(every_minute_job)
    forecaster = Forecaster([every_minute_job], scheduler)
    entries = forecaster.forecast(now=_utc())
    assert len(entries) == 1
    assert entries[0].job_name == "backup"


def test_forecast_next_run_in_future(every_minute_job, scheduler):
    scheduler.register(every_minute_job)
    now = _utc()
    forecaster = Forecaster([every_minute_job], scheduler)
    entries = forecaster.forecast(now=now)
    assert entries[0].next_run > now


def test_forecast_not_overdue_when_next_run_in_future(every_minute_job, scheduler):
    scheduler.register(every_minute_job)
    forecaster = Forecaster([every_minute_job], scheduler)
    entries = forecaster.forecast(now=_utc())
    assert not entries[0].is_overdue
    assert entries[0].overdue_by_seconds == 0.0


def test_forecast_overdue_when_last_seen_old(every_minute_job, scheduler):
    scheduler.register(every_minute_job)
    # Simulate last seen 10 minutes ago; next expected run was 9 minutes ago
    old_time = _utc(-600)
    scheduler.state["backup"].last_seen = old_time
    now = _utc()
    forecaster = Forecaster([every_minute_job], scheduler)
    entries = forecaster.forecast(now=now)
    assert entries[0].is_overdue
    assert entries[0].overdue_by_seconds > 0


def test_forecast_sorted_by_next_run():
    jobs = [
        JobConfig(name="hourly", cron="0 * * * *", grace_seconds=120),
        JobConfig(name="minutely", cron="* * * * *", grace_seconds=60),
    ]
    s = Scheduler()
    for j in jobs:
        s.register(j)
    forecaster = Forecaster(jobs, s)
    entries = forecaster.forecast(now=_utc())
    assert entries[0].next_run <= entries[1].next_run


def test_forecast_as_dict_contains_expected_keys(every_minute_job, scheduler):
    scheduler.register(every_minute_job)
    forecaster = Forecaster([every_minute_job], scheduler)
    d = forecaster.forecast(now=_utc())[0].as_dict()
    for key in ("job_name", "cron_expression", "next_run", "last_seen", "overdue_by_seconds", "is_overdue"):
        assert key in d


def test_forecast_last_seen_none_when_never_ran(every_minute_job, scheduler):
    scheduler.register(every_minute_job)
    forecaster = Forecaster([every_minute_job], scheduler)
    entries = forecaster.forecast(now=_utc())
    assert entries[0].last_seen is None
    assert entries[0].as_dict()["last_seen"] is None


def test_forecast_empty_when_no_jobs(scheduler):
    forecaster = Forecaster([], scheduler)
    entries = forecaster.forecast(now=_utc())
    assert entries == []
