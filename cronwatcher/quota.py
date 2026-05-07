"""Execution quota enforcement: limit how many times a job may run in a window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class QuotaPolicy:
    max_runs: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.max_runs <= 0:
            raise ValueError("max_runs must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class _QuotaState:
    timestamps: List[datetime] = field(default_factory=list)


class QuotaManager:
    """Track per-job run counts and enforce a rolling-window quota."""

    def __init__(self, policy: QuotaPolicy) -> None:
        self._policy = policy
        self._states: Dict[str, _QuotaState] = {}

    def _state(self, job_name: str) -> _QuotaState:
        if job_name not in self._states:
            self._states[job_name] = _QuotaState()
        return self._states[job_name]

    def _prune(self, state: _QuotaState, now: datetime) -> None:
        cutoff = now.timestamp() - self._policy.window_seconds
        state.timestamps = [t for t in state.timestamps if t.timestamp() >= cutoff]

    def record_run(self, job_name: str, when: datetime | None = None) -> None:
        """Record a run for *job_name* at *when* (default: now)."""
        now = when or _utcnow()
        state = self._state(job_name)
        self._prune(state, now)
        state.timestamps.append(now)

    def is_allowed(self, job_name: str, when: datetime | None = None) -> bool:
        """Return True if the job is still within its quota."""
        now = when or _utcnow()
        state = self._state(job_name)
        self._prune(state, now)
        return len(state.timestamps) < self._policy.max_runs

    def remaining(self, job_name: str, when: datetime | None = None) -> int:
        """Return how many more runs are allowed in the current window."""
        now = when or _utcnow()
        state = self._state(job_name)
        self._prune(state, now)
        return max(0, self._policy.max_runs - len(state.timestamps))

    def reset(self, job_name: str) -> None:
        """Clear quota state for *job_name*."""
        self._states.pop(job_name, None)
