"""SLA (Service Level Agreement) tracking for cron jobs.

Tracks whether jobs meet their expected success-rate and max-duration
thresholds over a rolling window, and reports violations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from cronwatcher.history import HistoryStore


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class SLAPolicy:
    """Defines the SLA requirements for a single job."""
    min_success_rate: float = 1.0   # 0.0 – 1.0
    max_duration_seconds: Optional[float] = None
    window_hours: float = 24.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.min_success_rate <= 1.0):
            raise ValueError("min_success_rate must be between 0.0 and 1.0")
        if self.max_duration_seconds is not None and self.max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")
        if self.window_hours <= 0:
            raise ValueError("window_hours must be positive")


@dataclass
class SLAViolation:
    job_name: str
    reason: str
    actual_value: float
    threshold: float
    checked_at: datetime = field(default_factory=_utcnow)

    def __str__(self) -> str:
        return (
            f"SLA violation [{self.job_name}]: {self.reason} "
            f"(actual={self.actual_value:.3f}, threshold={self.threshold:.3f})"
        )


class SLAChecker:
    """Checks SLA policies against recorded job history."""

    def __init__(self, store: HistoryStore) -> None:
        self._store = store
        self._policies: dict[str, SLAPolicy] = {}

    def register(self, job_name: str, policy: SLAPolicy) -> None:
        if not job_name:
            raise ValueError("job_name must not be empty")
        self._policies[job_name] = policy

    def policy_for(self, job_name: str) -> Optional[SLAPolicy]:
        return self._policies.get(job_name)

    def check(self, job_name: str, *, now: Optional[datetime] = None) -> List[SLAViolation]:
        """Return a list of SLA violations for *job_name* (empty = compliant)."""
        policy = self._policies.get(job_name)
        if policy is None:
            return []

        now = now or _utcnow()
        cutoff = now - timedelta(hours=policy.window_hours)
        records = [
            r for r in self._store.read_for_job(job_name)
            if r.timestamp >= cutoff
        ]

        violations: List[SLAViolation] = []

        if records:
            success_count = sum(1 for r in records if r.success)
            rate = success_count / len(records)
            if rate < policy.min_success_rate:
                violations.append(SLAViolation(
                    job_name=job_name,
                    reason="success rate below threshold",
                    actual_value=rate,
                    threshold=policy.min_success_rate,
                    checked_at=now,
                ))

        if policy.max_duration_seconds is not None:
            slow = [
                r for r in records
                if r.duration_seconds is not None
                and r.duration_seconds > policy.max_duration_seconds
            ]
            if slow:
                worst = max(r.duration_seconds for r in slow)  # type: ignore[type-var]
                violations.append(SLAViolation(
                    job_name=job_name,
                    reason="max duration exceeded",
                    actual_value=worst,
                    threshold=policy.max_duration_seconds,
                    checked_at=now,
                ))

        return violations

    def check_all(self, *, now: Optional[datetime] = None) -> dict[str, List[SLAViolation]]:
        """Check all registered jobs; returns mapping of job_name -> violations."""
        return {name: self.check(name, now=now) for name in self._policies}
