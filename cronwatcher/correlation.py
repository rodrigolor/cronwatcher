"""Job correlation: detect when multiple jobs fail together, suggesting a shared root cause."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CorrelationPolicy:
    window_seconds: int = 300  # failures within this window are considered correlated
    min_jobs: int = 2  # minimum jobs failing together to trigger a correlation alert

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.min_jobs < 2:
            raise ValueError("min_jobs must be at least 2")


@dataclass
class CorrelationEvent:
    jobs: List[str]
    detected_at: datetime
    window_seconds: int

    def __str__(self) -> str:
        return (
            f"Correlated failure of {len(self.jobs)} jobs "
            f"within {self.window_seconds}s window: {', '.join(sorted(self.jobs))}"
        )


class CorrelationDetector:
    """Tracks recent failures and emits CorrelationEvent when multiple jobs fail together."""

    def __init__(self, policy: CorrelationPolicy | None = None) -> None:
        self._policy = policy or CorrelationPolicy()
        # job_name -> list of failure timestamps
        self._failures: Dict[str, List[datetime]] = {}

    def record_failure(self, job_name: str, ts: datetime | None = None) -> None:
        """Record a failure for *job_name* at optional timestamp *ts*."""
        ts = ts or _utcnow()
        self._failures.setdefault(job_name, []).append(ts)

    def detect(self, reference_time: datetime | None = None) -> List[CorrelationEvent]:
        """Return correlation events visible from *reference_time*."""
        now = reference_time or _utcnow()
        cutoff = now - timedelta(seconds=self._policy.window_seconds)

        # Prune old entries and collect jobs with recent failures
        active: Dict[str, List[datetime]] = {}
        for job, timestamps in self._failures.items():
            recent = [t for t in timestamps if t >= cutoff]
            if recent:
                active[job] = recent
        self._failures = {**self._failures, **{k: v for k, v in active.items()}}

        if len(active) < self._policy.min_jobs:
            return []

        return [
            CorrelationEvent(
                jobs=list(active.keys()),
                detected_at=now,
                window_seconds=self._policy.window_seconds,
            )
        ]

    def clear(self, job_name: str) -> None:
        """Clear failure history for *job_name* (e.g. after recovery)."""
        self._failures.pop(job_name, None)
