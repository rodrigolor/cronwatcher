"""Execution duration profiling for cron jobs."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatcher.history import HistoryStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DurationProfile:
    job_name: str
    sample_count: int
    mean_seconds: float
    median_seconds: float
    stdev_seconds: float
    min_seconds: float
    max_seconds: float
    p95_seconds: float

    def __str__(self) -> str:
        return (
            f"{self.job_name}: mean={self.mean_seconds:.2f}s "
            f"median={self.median_seconds:.2f}s "
            f"p95={self.p95_seconds:.2f}s "
            f"min={self.min_seconds:.2f}s max={self.max_seconds:.2f}s "
            f"(n={self.sample_count})"
        )


@dataclass
class ProfilingPolicy:
    min_samples: int = 5

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")


class JobProfiler:
    """Computes duration statistics for jobs from history."""

    def __init__(self, store: HistoryStore, policy: Optional[ProfilingPolicy] = None) -> None:
        self._store = store
        self._policy = policy or ProfilingPolicy()

    def profile(self, job_name: str) -> Optional[DurationProfile]:
        records = [
            r for r in self._store.read_for_job(job_name)
            if r.duration_seconds is not None
        ]
        if len(records) < self._policy.min_samples:
            return None
        durations = [r.duration_seconds for r in records]
        sorted_d = sorted(durations)
        p95_idx = max(0, int(len(sorted_d) * 0.95) - 1)
        return DurationProfile(
            job_name=job_name,
            sample_count=len(durations),
            mean_seconds=statistics.mean(durations),
            median_seconds=statistics.median(durations),
            stdev_seconds=statistics.pstdev(durations),
            min_seconds=min(durations),
            max_seconds=max(durations),
            p95_seconds=sorted_d[p95_idx],
        )

    def profile_all(self, job_names: List[str]) -> Dict[str, DurationProfile]:
        result: Dict[str, DurationProfile] = {}
        for name in job_names:
            p = self.profile(name)
            if p is not None:
                result[name] = p
        return result
