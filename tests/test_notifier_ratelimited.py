"""Unit tests for cronwatcher.notifier_ratelimited."""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from cronwatcher.ratelimit import RateLimitPolicy, RateLimiter
from cronwatcher.notifier_ratelimited import RateLimitedNotifier


@pytest.fixture()
def inner():
    m = MagicMock()
    m.notify_missed = MagicMock()
    m.notify_failure = MagicMock()
    m.recover = MagicMock()
    return m


@pytest.fixture()
def policy():
    return RateLimitPolicy(max_alerts=2, window_seconds=3600)


def _limiter_always_allow(policy):
    lim = MagicMock(spec=RateLimiter)
    lim.is_allowed.return_value = True
    return lim


def _limiter_deny_after(n: int, policy):
    """Allow first n calls, deny the rest."""
    counter = {"c": 0}

    def _is_allowed(job_name):
        counter["c"] += 1
        return counter["c"] <= n

    lim = MagicMock(spec=RateLimiter)
    lim.is_allowed.side_effect = _is_allowed
    return lim


def test_missed_forwarded_when_allowed(inner, policy):
    lim = _limiter_always_allow(policy)
    rln = RateLimitedNotifier(inner, policy, limiter=lim)
    rln.notify_missed("job_a")
    inner.notify_missed.assert_called_once_with("job_a")


def test_missed_suppressed_when_denied(inner, policy):
    lim = _limiter_deny_after(0, policy)
    rln = RateLimitedNotifier(inner, policy, limiter=lim)
    rln.notify_missed("job_a")
    inner.notify_missed.assert_not_called()


def test_failure_forwarded_when_allowed(inner, policy):
    lim = _limiter_always_allow(policy)
    rln = RateLimitedNotifier(inner, policy, limiter=lim)
    rln.notify_failure("job_a", 1)
    inner.notify_failure.assert_called_once_with("job_a", 1)


def test_failure_suppressed_when_denied(inner, policy):
    lim = _limiter_deny_after(0, policy)
    rln = RateLimitedNotifier(inner, policy, limiter=lim)
    rln.notify_failure("job_a", 2)
    inner.notify_failure.assert_not_called()


def test_recover_resets_limiter_and_forwards(inner, policy):
    lim = MagicMock(spec=RateLimiter)
    rln = RateLimitedNotifier(inner, policy, limiter=lim)
    rln.recover("job_a")
    lim.reset.assert_called_once_with("job_a")
    inner.recover.assert_called_once_with("job_a")


def test_second_alert_allowed_within_limit(inner, policy):
    lim = _limiter_deny_after(2, policy)
    rln = RateLimitedNotifier(inner, policy, limiter=lim)
    rln.notify_missed("job_a")
    rln.notify_missed("job_a")
    rln.notify_missed("job_a")  # suppressed
    assert inner.notify_missed.call_count == 2
