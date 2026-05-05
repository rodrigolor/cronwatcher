"""Tests for cronwatcher.escalation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cronwatcher.escalation import EscalationManager, EscalationPolicy


def _utc(minutes_ago: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)


# ---------------------------------------------------------------------------
# EscalationPolicy validation
# ---------------------------------------------------------------------------

def test_policy_rejects_non_positive_cooldown():
    with pytest.raises(ValueError, match="cooldown_minutes"):
        EscalationPolicy(cooldown_minutes=0)


def test_policy_rejects_zero_max_escalations():
    with pytest.raises(ValueError, match="max_escalations"):
        EscalationPolicy(max_escalations=0)


# ---------------------------------------------------------------------------
# First failure always triggers alert
# ---------------------------------------------------------------------------

def test_first_failure_always_alerts():
    mgr = EscalationManager(EscalationPolicy())
    assert mgr.should_alert("backup") is True


# ---------------------------------------------------------------------------
# After recording an alert, cooldown applies
# ---------------------------------------------------------------------------

def test_no_alert_within_cooldown():
    mgr = EscalationManager(EscalationPolicy(cooldown_minutes=30))
    mgr.record_alert("backup")
    # Immediately after — still within cooldown
    assert mgr.should_alert("backup") is False


def test_alert_after_cooldown_elapsed():
    mgr = EscalationManager(EscalationPolicy(cooldown_minutes=30))
    mgr.record_alert("backup")

    # Simulate time passing beyond cooldown
    past = _utc(minutes_ago=31)
    mgr._states["backup"].last_alerted_at = past

    assert mgr.should_alert("backup") is True


# ---------------------------------------------------------------------------
# Max escalations cap
# ---------------------------------------------------------------------------

def test_max_escalations_cap():
    mgr = EscalationManager(EscalationPolicy(cooldown_minutes=1, max_escalations=2))
    mgr.record_alert("backup")
    mgr._states["backup"].last_alerted_at = _utc(minutes_ago=5)
    mgr.record_alert("backup")
    mgr._states["backup"].last_alerted_at = _utc(minutes_ago=5)

    # count == 2 == max_escalations → no more alerts
    assert mgr.should_alert("backup") is False


# ---------------------------------------------------------------------------
# clear() resets state
# ---------------------------------------------------------------------------

def test_clear_resets_state():
    mgr = EscalationManager(EscalationPolicy())
    mgr.record_alert("backup")
    assert mgr.escalation_count("backup") == 1

    mgr.clear("backup")
    assert mgr.escalation_count("backup") == 0
    assert mgr.should_alert("backup") is True  # treated as new failure


def test_clear_unknown_job_is_noop():
    mgr = EscalationManager(EscalationPolicy())
    mgr.clear("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# escalation_count
# ---------------------------------------------------------------------------

def test_escalation_count_increments():
    mgr = EscalationManager(EscalationPolicy(cooldown_minutes=1))
    assert mgr.escalation_count("job") == 0
    mgr.record_alert("job")
    assert mgr.escalation_count("job") == 1
    mgr._states["job"].last_alerted_at = _utc(minutes_ago=2)
    mgr.record_alert("job")
    assert mgr.escalation_count("job") == 2
