"""Tests for cronwatcher.suppression and cronwatcher.notifier_suppression."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.suppression import SuppressionRegistry, SuppressionRule
from cronwatcher.notifier_suppression import SuppressingNotifier


def _utc(**kwargs) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(**kwargs)


NOW = _utc()


# ---------------------------------------------------------------------------
# SuppressionRule
# ---------------------------------------------------------------------------

def test_active_rule_is_active():
    rule = SuppressionRule("job", expires_at=_utc(hours=1))
    assert rule.is_active(now=NOW) is True


def test_expired_rule_is_not_active():
    rule = SuppressionRule("job", expires_at=_utc(hours=-1))
    assert rule.is_active(now=NOW) is False


def test_as_dict_contains_expected_keys():
    rule = SuppressionRule("myjob", expires_at=_utc(hours=2), reason="deploy")
    d = rule.as_dict()
    assert d["job_name"] == "myjob"
    assert d["reason"] == "deploy"
    assert "expires_at" in d


# ---------------------------------------------------------------------------
# SuppressionRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> SuppressionRegistry:
    return SuppressionRegistry()


def test_is_suppressed_when_active_rule_exists(registry):
    registry.add(SuppressionRule("backup", expires_at=_utc(hours=1)))
    assert registry.is_suppressed("backup", now=NOW) is True


def test_is_not_suppressed_when_no_rule(registry):
    assert registry.is_suppressed("backup", now=NOW) is False


def test_is_not_suppressed_when_rule_expired(registry):
    registry.add(SuppressionRule("backup", expires_at=_utc(hours=-1)))
    assert registry.is_suppressed("backup", now=NOW) is False


def test_remove_expired_clears_old_rules(registry):
    registry.add(SuppressionRule("a", expires_at=_utc(hours=-2)))
    registry.add(SuppressionRule("b", expires_at=_utc(hours=2)))
    removed = registry.remove_expired(now=NOW)
    assert removed == 1
    assert registry.is_suppressed("b", now=NOW) is True
    assert registry.is_suppressed("a", now=NOW) is False


def test_active_rules_returns_only_live_rules(registry):
    registry.add(SuppressionRule("x", expires_at=_utc(hours=1)))
    registry.add(SuppressionRule("y", expires_at=_utc(hours=-1)))
    active = registry.active_rules(now=NOW)
    assert len(active) == 1
    assert active[0].job_name == "x"


# ---------------------------------------------------------------------------
# SuppressingNotifier
# ---------------------------------------------------------------------------

@pytest.fixture()
def inner():
    m = MagicMock()
    m.notify_missed = MagicMock()
    m.notify_failure = MagicMock()
    m.recover = MagicMock()
    return m


def test_notify_missed_forwarded_when_not_suppressed(inner):
    reg = SuppressionRegistry()
    sn = SuppressingNotifier(inner, reg)
    sn.notify_missed("job1")
    inner.notify_missed.assert_called_once_with("job1")


def test_notify_missed_suppressed_when_rule_active(inner):
    reg = SuppressionRegistry()
    reg.add(SuppressionRule("job1", expires_at=_utc(hours=1)))
    sn = SuppressingNotifier(inner, reg)
    sn.notify_missed("job1")
    inner.notify_missed.assert_not_called()


def test_notify_failure_suppressed(inner):
    reg = SuppressionRegistry()
    reg.add(SuppressionRule("job2", expires_at=_utc(hours=1)))
    sn = SuppressingNotifier(inner, reg)
    sn.notify_failure("job2", "exit 1")
    inner.notify_failure.assert_not_called()


def test_notify_failure_forwarded_when_not_suppressed(inner):
    reg = SuppressionRegistry()
    sn = SuppressingNotifier(inner, reg)
    sn.notify_failure("job2", "exit 1")
    inner.notify_failure.assert_called_once_with("job2", "exit 1")


def test_recover_always_forwarded(inner):
    reg = SuppressionRegistry()
    reg.add(SuppressionRule("job3", expires_at=_utc(hours=1)))
    sn = SuppressingNotifier(inner, reg)
    sn.recover("job3")
    inner.recover.assert_called_once_with("job3")
