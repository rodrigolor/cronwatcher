"""Integration tests for Watcher using real Scheduler and Notifier."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cronwatcher.config import AlertConfig, CronWatcherConfig, JobConfig
from cronwatcher.notifier import Notifier
from cronwatcher.scheduler import Scheduler
from cronwatcher.watcher import Watcher


@pytest.fixture()
def stale_job_config() -> CronWatcherConfig:
    """A job that runs every minute with a very short grace period."""
    return CronWatcherConfig(
        jobs=[JobConfig(name="heartbeat", schedule="* * * * *", grace_seconds=10)],
        alerts=AlertConfig(enabled=True, log_level="WARNING"),
        poll_interval=1.0,
    )


def test_watcher_detects_missed_job_via_real_scheduler(stale_job_config, caplog):
    """Watcher should log a warning when a job hasn't been seen within grace period."""
    import logging

    scheduler = Scheduler()
    notifier = Notifier(stale_job_config.alerts)
    watcher = Watcher(stale_job_config, scheduler=scheduler, notifier=notifier)

    # Simulate last execution far in the past
    past = datetime.now(tz=timezone.utc) - timedelta(minutes=10)
    scheduler.record_execution("heartbeat", at=past)

    with caplog.at_level(logging.WARNING):
        watcher.tick()

    assert any("heartbeat" in r.message for r in caplog.records)


def test_watcher_no_alert_when_job_recent(stale_job_config, caplog):
    """No missed alert when job executed within grace period."""
    import logging

    scheduler = Scheduler()
    notifier = Notifier(stale_job_config.alerts)
    watcher = Watcher(stale_job_config, scheduler=scheduler, notifier=notifier)

    # Simulate recent execution
    now = datetime.now(tz=timezone.utc)
    scheduler.record_execution("heartbeat", at=now)

    with caplog.at_level(logging.WARNING):
        watcher.tick()

    missed_logs = [r for r in caplog.records if "Missed" in r.message]
    assert len(missed_logs) == 0
