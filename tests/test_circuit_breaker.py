"""Tests for cronwatcher.circuit_breaker."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cronwatcher.circuit_breaker import CircuitBreaker, CircuitBreakerPolicy, _State


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)


# ---------------------------------------------------------------------------
# Policy validation
# ---------------------------------------------------------------------------

def test_policy_rejects_zero_threshold():
    with pytest.raises(ValueError, match="failure_threshold"):
        CircuitBreakerPolicy(failure_threshold=0)


def test_policy_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="recovery_timeout"):
        CircuitBreakerPolicy(recovery_timeout=0)


# ---------------------------------------------------------------------------
# Closed state
# ---------------------------------------------------------------------------

def test_initially_closed_and_allowed():
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=2, recovery_timeout=30))
    assert cb.is_allowed("email") is True
    assert cb.state_for("email") == _State.CLOSED


def test_failures_below_threshold_stay_closed():
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=3, recovery_timeout=30))
    cb.record_failure("email")
    cb.record_failure("email")
    assert cb.state_for("email") == _State.CLOSED
    assert cb.is_allowed("email") is True


# ---------------------------------------------------------------------------
# Open state
# ---------------------------------------------------------------------------

def test_threshold_reached_opens_circuit():
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=2, recovery_timeout=30))
    cb.record_failure("email")
    cb.record_failure("email")
    assert cb.state_for("email") == _State.OPEN


def test_open_circuit_blocks_calls():
    now = _utc()
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=60))
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=now):
        cb.record_failure("slack")
    # Still within recovery window
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=_utc(30)):
        assert cb.is_allowed("slack") is False


# ---------------------------------------------------------------------------
# Half-open / recovery
# ---------------------------------------------------------------------------

def test_open_transitions_to_half_open_after_timeout():
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=60))
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=_utc(0)):
        cb.record_failure("slack")
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=_utc(61)):
        allowed = cb.is_allowed("slack")
    assert allowed is True
    assert cb.state_for("slack") == _State.HALF_OPEN


def test_success_in_half_open_closes_circuit():
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=60))
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=_utc(0)):
        cb.record_failure("slack")
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=_utc(61)):
        cb.is_allowed("slack")  # transitions to half-open
        cb.record_success("slack")
    assert cb.state_for("slack") == _State.CLOSED


def test_failure_in_half_open_reopens_circuit():
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=60))
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=_utc(0)):
        cb.record_failure("slack")
    with patch("cronwatcher.circuit_breaker._utcnow", return_value=_utc(61)):
        cb.is_allowed("slack")  # transitions to half-open
        cb.record_failure("slack")
    assert cb.state_for("slack") == _State.OPEN


# ---------------------------------------------------------------------------
# Independent backends
# ---------------------------------------------------------------------------

def test_independent_backends_do_not_interfere():
    cb = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=2, recovery_timeout=30))
    cb.record_failure("email")
    cb.record_failure("email")
    assert cb.state_for("email") == _State.OPEN
    assert cb.state_for("slack") == _State.CLOSED
    assert cb.is_allowed("slack") is True
