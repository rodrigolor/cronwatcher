"""Tests for cronwatcher.retry."""
from __future__ import annotations

import pytest

from cronwatcher.retry import RetryPolicy, RetryManager


# ---------------------------------------------------------------------------
# RetryPolicy validation
# ---------------------------------------------------------------------------

def test_policy_rejects_zero_max_retries():
    with pytest.raises(ValueError, match="max_retries"):
        RetryPolicy(max_retries=0)


def test_policy_rejects_zero_delay():
    with pytest.raises(ValueError, match="retry_delay_seconds"):
        RetryPolicy(retry_delay_seconds=0)


def test_policy_accepts_valid_values():
    p = RetryPolicy(max_retries=2, retry_delay_seconds=30)
    assert p.max_retries == 2
    assert p.retry_delay_seconds == 30


# ---------------------------------------------------------------------------
# RetryManager behaviour
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager():
    return RetryManager(RetryPolicy(max_retries=3, retry_delay_seconds=60))


def test_first_failure_does_not_alert(manager):
    assert manager.record_failure("backup") is False


def test_second_failure_does_not_alert(manager):
    manager.record_failure("backup")
    assert manager.record_failure("backup") is False


def test_third_failure_triggers_alert(manager):
    manager.record_failure("backup")
    manager.record_failure("backup")
    assert manager.record_failure("backup") is True


def test_alert_fires_only_once_per_run(manager):
    for _ in range(3):
        manager.record_failure("backup")
    # Fourth failure — alert already sent, should not fire again
    assert manager.record_failure("backup") is False


def test_is_alerting_after_threshold(manager):
    for _ in range(3):
        manager.record_failure("backup")
    assert manager.is_alerting("backup") is True


def test_consecutive_failures_counter(manager):
    manager.record_failure("backup")
    manager.record_failure("backup")
    assert manager.consecutive_failures("backup") == 2


def test_success_resets_state(manager):
    for _ in range(3):
        manager.record_failure("backup")
    manager.record_success("backup")
    assert manager.consecutive_failures("backup") == 0
    assert manager.is_alerting("backup") is False


def test_alert_fires_again_after_success_and_new_failures(manager):
    for _ in range(3):
        manager.record_failure("backup")
    manager.record_success("backup")
    manager.record_failure("backup")
    manager.record_failure("backup")
    assert manager.record_failure("backup") is True


def test_independent_job_states(manager):
    manager.record_failure("job_a")
    manager.record_failure("job_a")
    manager.record_failure("job_a")  # triggers alert for job_a
    # job_b should still be at zero
    assert manager.consecutive_failures("job_b") == 0
    assert manager.is_alerting("job_b") is False
