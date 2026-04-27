"""Unit tests for cronwatcher.watcher.Watcher."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from cronwatcher.config import AlertConfig, CronWatcherConfig, JobConfig
from cronwatcher.watcher import Watcher


@pytest.fixture()
def simple_config() -> CronWatcherConfig:
    return CronWatcherConfig(
        jobs=[
            JobConfig(name="backup", schedule="0 2 * * *", grace_seconds=120),
            JobConfig(name="cleanup", schedule="*/10 * * * *", grace_seconds=30),
        ],
        alerts=AlertConfig(enabled=True),
        poll_interval=5.0,
    )


@pytest.fixture()
def mock_scheduler():
    sched = MagicMock()
    sched.check_missed.return_value = []
    return sched


@pytest.fixture()
def mock_notifier():
    return MagicMock()


def test_watcher_registers_all_jobs(simple_config, mock_scheduler, mock_notifier):
    Watcher(simple_config, scheduler=mock_scheduler, notifier=mock_notifier)
    assert mock_scheduler.register.call_count == 2
    registered_names = {c.args[0].name for c in mock_scheduler.register.call_args_list}
    assert registered_names == {"backup", "cleanup"}


def test_tick_notifies_missed_jobs(simple_config, mock_scheduler, mock_notifier):
    mock_scheduler.check_missed.return_value = ["backup"]
    watcher = Watcher(simple_config, scheduler=mock_scheduler, notifier=mock_notifier)
    watcher.tick()
    mock_notifier.notify_missed.assert_called_once_with("backup")


def test_tick_no_missed_jobs(simple_config, mock_scheduler, mock_notifier):
    mock_scheduler.check_missed.return_value = []
    watcher = Watcher(simple_config, scheduler=mock_scheduler, notifier=mock_notifier)
    watcher.tick()
    mock_notifier.notify_missed.assert_not_called()


def test_tick_multiple_missed_jobs(simple_config, mock_scheduler, mock_notifier):
    mock_scheduler.check_missed.return_value = ["backup", "cleanup"]
    watcher = Watcher(simple_config, scheduler=mock_scheduler, notifier=mock_notifier)
    watcher.tick()
    assert mock_notifier.notify_missed.call_count == 2
    mock_notifier.notify_missed.assert_any_call("backup")
    mock_notifier.notify_missed.assert_any_call("cleanup")


def test_stop_sets_running_false(simple_config, mock_scheduler, mock_notifier):
    watcher = Watcher(simple_config, scheduler=mock_scheduler, notifier=mock_notifier)
    watcher._running = True
    watcher.stop()
    assert watcher._running is False


def test_run_calls_tick_and_sleeps(simple_config, mock_scheduler, mock_notifier):
    call_count = 0

    def fake_sleep(_):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            mock_notifier.stop_signal = True
            watcher.stop()

    watcher = Watcher(simple_config, scheduler=mock_scheduler, notifier=mock_notifier)
    with patch("cronwatcher.watcher.time.sleep", side_effect=fake_sleep):
        watcher.run(poll_interval=0.01)

    assert call_count >= 2
    assert mock_scheduler.check_missed.call_count >= 2
