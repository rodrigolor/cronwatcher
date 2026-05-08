"""Trend analysis for job execution durations over time."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.history import HistoryStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TrendResult:
    job_name: str
    sample_count: int
    mean_duration: float
    slope: float          # seconds per run (positive = getting slower)
    is_degrading: bool
    latest_duration: Optional[float]

    def __str__(self) -> str:
        direction = "degrading" if self.is_degrading else "stable"
        return (
            f"{self.job_name}: {direction} | "
            f"mean={self.mean_duration:.1f}s slope={self.slope:+.3f}s/run "
            f"(n={self.sample_count})"
        )


@dataclass
class TrendPolicy:
    min_samples: int = 5
    degradation_slope_threshold: float = 1.0  # seconds per run

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be >= 2")
        if self.degradation_slope_threshold <= 0:
            raise ValueError("degradation_slope_threshold must be positive")


class TrendAnalyzer:
    """Detects whether job execution durations are trending upward."""

    def __init__(self, store: HistoryStore, policy: TrendPolicy | None = None) -> None:
        self._store = store
        self._policy = policy or TrendPolicy()

    def analyze(self, job_name: str) -> Optional[TrendResult]:
        records = [
            r for r in self._store.read_for_job(job_name)
            if r.duration_seconds is not None
        ]
        if len(records) < self._policy.min_samples:
            return None

        durations: List[float] = [r.duration_seconds for r in records]  # type: ignore[misc]
        n = len(durations)
        mean_d = sum(durations) / n

        # Least-squares slope
        xs = list(range(n))
        mean_x = (n - 1) / 2.0
        num = sum((xs[i] - mean_x) * (durations[i] - mean_d) for i in range(n))
        den = sum((xs[i] - mean_x) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0.0

        is_degrading = slope >= self._policy.degradation_slope_threshold
        return TrendResult(
            job_name=job_name,
            sample_count=n,
            mean_duration=mean_d,
            slope=slope,
            is_degrading=is_degrading,
            latest_duration=durations[-1],
        )

    def analyze_all(self, job_names: List[str]) -> List[TrendResult]:
        results = []
        for name in job_names:
            r = self.analyze(name)
            if r is not None:
                results.append(r)
        return sorted(results, key=lambda r: r.slope, reverse=True)
