"""Retry policy for failed cron jobs — tracks consecutive failures and
determines whether a job should be retried before alerting."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RetryPolicy:
    max_retries: int = 3
    retry_delay_seconds: int = 60

    def __post_init__(self) -> None:
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if self.retry_delay_seconds < 1:
            raise ValueError("retry_delay_seconds must be >= 1")


@dataclass
class _RetryState:
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    alerted: bool = False


class RetryManager:
    """Tracks per-job retry state and decides when an alert should fire."""

    def __init__(self, policy: RetryPolicy) -> None:
        self._policy = policy
        self._states: Dict[str, _RetryState] = {}

    def _state(self, job_name: str) -> _RetryState:
        if job_name not in self._states:
            self._states[job_name] = _RetryState()
        return self._states[job_name]

    def record_failure(self, job_name: str) -> bool:
        """Record a failure for *job_name*.

        Returns True when the caller should fire an alert (i.e. all retries
        have been exhausted and no alert has been sent for this failure run).
        """
        state = self._state(job_name)
        now = _utcnow()

        # If enough time has passed since the last failure, reset the counter
        # so we treat this as a fresh run.
        if (
            state.last_failure_at is not None
            and (now - state.last_failure_at).total_seconds()
            > self._policy.retry_delay_seconds
            and state.consecutive_failures < self._policy.max_retries
        ):
            state.consecutive_failures = 0
            state.alerted = False

        state.consecutive_failures += 1
        state.last_failure_at = now

        if state.consecutive_failures >= self._policy.max_retries and not state.alerted:
            state.alerted = True
            return True
        return False

    def record_success(self, job_name: str) -> None:
        """Reset retry state after a successful execution."""
        self._states[job_name] = _RetryState()

    def consecutive_failures(self, job_name: str) -> int:
        return self._state(job_name).consecutive_failures

    def is_alerting(self, job_name: str) -> bool:
        """Return True if an alert has already been fired for the current run."""
        return self._state(job_name).alerted
