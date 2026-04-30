"""Tests for cronwatcher.digest.DigestSender."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.digest import DigestSender
from cronwatcher.config import CronWatcherConfig, JobConfig, AlertConfig
from cronwatcher.history import HistoryStore, ExecutionRecord


UTC = timezone.utc


def _utc(offset_seconds: int = 0) -> datetime:
    return datetime(2024, 1, 10, 12, 0, 0, tzinfo=UTC) + timedelta(seconds=offset_seconds)


@pytest.fixture()
def config() -> CronWatcherConfig:
    return CronWatcherConfig(
        jobs=[
            JobConfig(name="backup", schedule="0 2 * * *", grace_period=300),
            JobConfig(name="cleanup", schedule="0 3 * * *", grace_period=300),
        ],
        alert=AlertConfig(enabled=False, recipients=[]),
    )


@pytest.fixture()
def store(tmp_path) -> HistoryStore:
    s = HistoryStore(tmp_path)
    s.record(ExecutionRecord(job_name="backup", success=True, timestamp=_utc(-3600)))
    s.record(ExecutionRecord(job_name="backup", success=False, timestamp=_utc(-1800)))
    s.record(ExecutionRecord(job_name="cleanup", success=True, timestamp=_utc(-900)))
    return s


@pytest.fixture()
def notifier() -> MagicMock:
    n = MagicMock()
    n.notify_digest = MagicMock()
    return n


def test_digest_sent_on_first_call(config, store, notifier):
    sender = DigestSender(config, store, notifier, interval_seconds=3600)
    result = sender.maybe_send(now=_utc())
    assert result is True
    notifier.notify_digest.assert_called_once()


def test_digest_not_sent_before_interval(config, store, notifier):
    sender = DigestSender(config, store, notifier, interval_seconds=3600)
    sender.maybe_send(now=_utc())
    notifier.notify_digest.reset_mock()

    result = sender.maybe_send(now=_utc(offset_seconds=1800))
    assert result is False
    notifier.notify_digest.assert_not_called()


def test_digest_sent_after_interval_elapsed(config, store, notifier):
    sender = DigestSender(config, store, notifier, interval_seconds=3600)
    sender.maybe_send(now=_utc())
    notifier.notify_digest.reset_mock()

    result = sender.maybe_send(now=_utc(offset_seconds=3601))
    assert result is True
    notifier.notify_digest.assert_called_once()


def test_digest_text_contains_job_names(config, store, notifier):
    sender = DigestSender(config, store, notifier, interval_seconds=3600)
    sender.maybe_send(now=_utc())

    call_args = notifier.notify_digest.call_args[0][0]
    assert "backup" in call_args
    assert "cleanup" in call_args


def test_digest_uses_utc_now_by_default(config, store, notifier):
    sender = DigestSender(config, store, notifier, interval_seconds=0)
    result = sender.maybe_send()
    assert result is True
