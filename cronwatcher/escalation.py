"""Escalation policy: re-alert if a job remains failing after a cooldown."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EscalationPolicy:
    """Defines how long to wait before re-sending an alert for a still-failing job."""

    cooldown_minutes: int = 60
    max_escalations: int = 3

    def __post_init__(self) -> None:
        if self.cooldown_minutes <= 0:
            raise ValueError("cooldown_minutes must be positive")
        if self.max_escalations < 1:
            raise ValueError("max_escalations must be at least 1")


@dataclass
class _EscalationState:
    count: int = 0
    last_alerted_at: Optional[datetime] = None


class EscalationManager:
    """Tracks per-job escalation state and decides whether to re-alert."""

    def __init__(self, policy: EscalationPolicy) -> None:
        self._policy = policy
        self._states: Dict[str, _EscalationState] = {}

    def should_alert(self, job_name: str) -> bool:
        """Return True if an alert should be (re-)sent for *job_name*."""
        state = self._states.get(job_name)
        if state is None:
            return True  # first failure — always alert

        if state.count >= self._policy.max_escalations:
            return False  # cap reached

        if state.last_alerted_at is None:
            return True

        elapsed = (_utcnow() - state.last_alerted_at).total_seconds() / 60
        return elapsed >= self._policy.cooldown_minutes

    def record_alert(self, job_name: str) -> None:
        """Mark that an alert was just sent for *job_name*."""
        state = self._states.setdefault(job_name, _EscalationState())
        state.count += 1
        state.last_alerted_at = _utcnow()

    def clear(self, job_name: str) -> None:
        """Reset escalation state when a job recovers."""
        self._states.pop(job_name, None)

    def escalation_count(self, job_name: str) -> int:
        """Return how many times an alert has been sent for *job_name*."""
        state = self._states.get(job_name)
        return state.count if state else 0
