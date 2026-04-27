"""Tests for cronwatcher.alerts and cronwatcher.notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import datetime

import pytest

from cronwatcher.alerts import (
    AlertDispatcher,
    EmailAlertBackend,
    LogAlertBackend,
    build_dispatcher,
)
from cronwatcher.config import AlertConfig
from cronwatcher.notifier import Notifier
from cronwatcher.scheduler import JobState


# ---------------------------------------------------------------------------
# LogAlertBackend
# ---------------------------------------------------------------------------

def test_log_backend_calls_logger(caplog):
    import logging
    backend = LogAlertBackend()
    with caplog.at_level(logging.WARNING, logger="cronwatcher.alerts"):
        backend.send("Test subject", "Test body")
    assert "Test subject" in caplog.text


# ---------------------------------------------------------------------------
# EmailAlertBackend
# ---------------------------------------------------------------------------

@pytest.fixture()
def email_config():
    return AlertConfig(
        enabled=True,
        recipients=["ops@example.com"],
        from_address="cron@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_tls=True,
        smtp_user="user",
        smtp_password="secret",
    )


def test_email_backend_sends_message(email_config):
    backend = EmailAlertBackend(email_config)
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        backend.send("Subject", "Body")
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "secret")
        mock_smtp.send_message.assert_called_once()


def test_email_backend_logs_on_smtp_error(email_config, caplog):
    import logging
    backend = EmailAlertBackend(email_config)
    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
        with caplog.at_level(logging.ERROR, logger="cronwatcher.alerts"):
            backend.send("Subject", "Body")  # must not raise
    assert "Failed to send alert email" in caplog.text


# ---------------------------------------------------------------------------
# AlertDispatcher
# ---------------------------------------------------------------------------

def test_dispatcher_calls_all_backends():
    b1, b2 = MagicMock(), MagicMock()
    dispatcher = AlertDispatcher([b1, b2])
    dispatcher.dispatch("s", "b")
    b1.send.assert_called_once_with("s", "b")
    b2.send.assert_called_once_with("s", "b")


def test_build_dispatcher_no_config():
    dispatcher = build_dispatcher(None)
    assert len(dispatcher.backends) == 1  # only LogAlertBackend


def test_build_dispatcher_with_email_config(email_config):
    dispatcher = build_dispatcher(email_config)
    assert len(dispatcher.backends) == 2


# ---------------------------------------------------------------------------
# Notifier
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_dispatcher():
    return MagicMock(spec=AlertDispatcher)


def test_notifier_missed_contains_job_name(mock_dispatcher):
    notifier = Notifier(mock_dispatcher)
    state = JobState(schedule="* * * * *")
    now = datetime.datetime(2024, 1, 15, 12, 0, 0)
    notifier.notify_missed("backup", state, now=now)
    subject, body = mock_dispatcher.dispatch.call_args[0]
    assert "backup" in subject
    assert "backup" in body
    assert "never" in body


def test_notifier_failure_contains_exit_code(mock_dispatcher):
    notifier = Notifier(mock_dispatcher)
    notifier.notify_failure("cleanup", exit_code=1, output="error output")
    subject, body = mock_dispatcher.dispatch.call_args[0]
    assert "cleanup" in subject
    assert "1" in body
    assert "error output" in body
