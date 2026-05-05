"""Integration tests for EscalatingNotifier."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest

from cronwatcher.escalation import EscalationPolicy
from cronwatcher.notifier_escalation import EscalatingNotifier


@pytest.fixture()
def notifier_mock():
    m = MagicMock()
    m.notify_missed = MagicMock()
    m.notify_failure = MagicMock()
    return m


@pytest.fixture()
def en(notifier_mock):
    policy = EscalationPolicy(cooldown_minutes=30, max_escalations=3)
    return EscalatingNotifier(notifier_mock, policy)


# ---------------------------------------------------------------------------
# notify_missed
# ---------------------------------------------------------------------------

def test_first_missed_alert_forwarded(en, notifier_mock):
    result = en.notify_missed("backup")
    assert result is True
    notifier_mock.notify_missed.assert_called_once_with("backup")


def test_second_missed_alert_suppressed_in_cooldown(en, notifier_mock):
    en.notify_missed("backup")
    result = en.notify_missed("backup")  # still in cooldown
    assert result is False
    assert notifier_mock.notify_missed.call_count == 1


def test_missed_alert_resent_after_cooldown(en, notifier_mock):
    en.notify_missed("backup")
    # Manually expire the cooldown
    from datetime import timezone
    from datetime import datetime
    en._manager._states["backup"].last_alerted_at = (
        datetime.now(timezone.utc) - timedelta(minutes=31)
    )
    result = en.notify_missed("backup")
    assert result is True
    assert notifier_mock.notify_missed.call_count == 2


# ---------------------------------------------------------------------------
# notify_failure
# ---------------------------------------------------------------------------

def test_first_failure_alert_forwarded(en, notifier_mock):
    result = en.notify_failure("etl", 1)
    assert result is True
    notifier_mock.notify_failure.assert_called_once_with("etl", 1)


def test_failure_alert_suppressed_in_cooldown(en, notifier_mock):
    en.notify_failure("etl", 1)
    result = en.notify_failure("etl", 1)
    assert result is False
    assert notifier_mock.notify_failure.call_count == 1


# ---------------------------------------------------------------------------
# recover() resets state
# ---------------------------------------------------------------------------

def test_recover_allows_fresh_alert(en, notifier_mock):
    en.notify_missed("backup")
    en.recover("backup")
    result = en.notify_missed("backup")
    assert result is True
    assert notifier_mock.notify_missed.call_count == 2


# ---------------------------------------------------------------------------
# escalation_count
# ---------------------------------------------------------------------------

def test_escalation_count_tracked(en, notifier_mock):
    assert en.escalation_count("backup") == 0
    en.notify_missed("backup")
    assert en.escalation_count("backup") == 1


# ---------------------------------------------------------------------------
# max escalations cap
# ---------------------------------------------------------------------------

def test_max_escalations_stops_alerts(en, notifier_mock):
    from datetime import timezone, datetime

    for _ in range(3):
        en.notify_missed("backup")
        en._manager._states["backup"].last_alerted_at = (
            datetime.now(timezone.utc) - timedelta(minutes=31)
        )

    # 4th attempt should be suppressed
    result = en.notify_missed("backup")
    assert result is False
    assert notifier_mock.notify_missed.call_count == 3
