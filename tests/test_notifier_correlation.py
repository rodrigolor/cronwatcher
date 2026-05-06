"""Unit tests for cronwatcher.notifier_correlation."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call

import pytest

from cronwatcher.correlation import CorrelationDetector, CorrelationPolicy
from cronwatcher.notifier_correlation import CorrelatingNotifier


def _make_notifier():
    inner = MagicMock()
    policy = CorrelationPolicy(window_seconds=60, min_jobs=2)
    cn = CorrelatingNotifier(inner, policy=policy)
    return cn, inner


def test_notify_missed_forwards_to_inner() -> None:
    cn, inner = _make_notifier()
    cn.notify_missed("job_a")
    inner.notify_missed.assert_called_once_with("job_a")


def test_notify_failure_forwards_to_inner() -> None:
    cn, inner = _make_notifier()
    cn.notify_failure("job_a", 1)
    inner.notify_failure.assert_called_once_with("job_a", 1)


def test_correlation_logged_on_multiple_failures(caplog) -> None:
    import logging
    cn, inner = _make_notifier()
    with caplog.at_level(logging.WARNING, logger="cronwatcher.notifier_correlation"):
        cn.notify_missed("job_a")
        cn.notify_missed("job_b")
    assert any("correlation" in r.message.lower() for r in caplog.records)


def test_no_correlation_log_for_single_failure(caplog) -> None:
    import logging
    cn, inner = _make_notifier()
    with caplog.at_level(logging.WARNING, logger="cronwatcher.notifier_correlation"):
        cn.notify_missed("job_a")
    correlation_logs = [r for r in caplog.records if "correlation" in r.message.lower()]
    assert correlation_logs == []


def test_recover_clears_failure_history(caplog) -> None:
    import logging
    cn, inner = _make_notifier()
    cn.notify_missed("job_a")
    cn.recover("job_a")
    # After clearing job_a, only job_b remains — no correlation event
    with caplog.at_level(logging.WARNING, logger="cronwatcher.notifier_correlation"):
        cn.notify_missed("job_b")
    correlation_warns = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "correlation" in r.message.lower()
    ]
    assert correlation_warns == []


def test_recover_logs_info(caplog) -> None:
    import logging
    cn, inner = _make_notifier()
    with caplog.at_level(logging.INFO, logger="cronwatcher.notifier_correlation"):
        cn.recover("job_x")
    assert any("job_x" in r.message and "recovered" in r.message for r in caplog.records)
