"""Rate limiting for alert notifications to prevent alert storms."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RateLimitPolicy:
    """Defines how many alerts are allowed per window (in seconds)."""
    max_alerts: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.max_alerts < 1:
            raise ValueError("max_alerts must be >= 1")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")


@dataclass
class _RateLimitState:
    count: int = 0
    window_start: Optional[datetime] = None


class RateLimiter:
    """Tracks per-job alert counts and suppresses excess alerts."""

    def __init__(self, policy: RateLimitPolicy) -> None:
        self._policy = policy
        self._states: Dict[str, _RateLimitState] = {}

    def _state(self, job_name: str) -> _RateLimitState:
        if job_name not in self._states:
            self._states[job_name] = _RateLimitState()
        return self._states[job_name]

    def is_allowed(self, job_name: str) -> bool:
        """Return True if an alert for job_name is allowed right now."""
        now = _utcnow()
        state = self._state(job_name)

        if state.window_start is None:
            state.window_start = now
            state.count = 0

        elapsed = (now - state.window_start).total_seconds()
        if elapsed >= self._policy.window_seconds:
            # Reset window
            state.window_start = now
            state.count = 0

        if state.count < self._policy.max_alerts:
            state.count += 1
            return True

        return False

    def reset(self, job_name: str) -> None:
        """Clear rate-limit state for a job (e.g. on recovery)."""
        self._states.pop(job_name, None)

    def suppressed_count(self, job_name: str) -> int:
        """Return how many alerts have been suppressed in the current window."""
        state = self._state(job_name)
        if state.count <= self._policy.max_alerts:
            return 0
        return state.count - self._policy.max_alerts
