"""Integration-style tests wiring Notifier → AlertDispatcher → LogAlertBackend."""

from __future__ import annotations

import datetime
import logging

import pytest

from cronwatcher.alerts import build_dispatcher
from cronwatcher.config import AlertConfig
from cronwatcher.notifier import Notifier
from cronwatcher.scheduler import JobState


@pytest.fixture()
def notifier_log_only():
    dispatcher = build_dispatcher(None)
    return Notifier(dispatcher)


def test_missed_alert_logged(notifier_log_only, caplog):
    state = JobState(schedule="0 * * * *")
    state.last_seen = datetime.datetime(2024, 1, 15, 10, 0, 0)
    now = datetime.datetime(2024, 1, 15, 12, 0, 0)
    with caplog.at_level(logging.WARNING, logger="cronwatcher.alerts"):
        notifier_log_only.notify_missed("hourly-report", state, now=now)
    assert "hourly-report" in caplog.text
    assert "Missed job" in caplog.text


def test_failure_alert_logged(notifier_log_only, caplog):
    with caplog.at_level(logging.WARNING, logger="cronwatcher.alerts"):
        notifier_log_only.notify_failure("db-backup", exit_code=2)
    assert "db-backup" in caplog.text
    assert "Job failed" in caplog.text


def test_alert_config_disabled_no_email_backend():
    cfg = AlertConfig(enabled=False, recipients=["x@x.com"])
    dispatcher = build_dispatcher(cfg)
    # disabled → only LogAlertBackend
    assert len(dispatcher.backends) == 1


def test_alert_config_enabled_no_recipients_no_email_backend():
    cfg = AlertConfig(enabled=True, recipients=[])
    dispatcher = build_dispatcher(cfg)
    assert len(dispatcher.backends) == 1
