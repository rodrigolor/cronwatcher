"""Anomaly detection: flag jobs whose runtime duration deviates significantly
from their historical baseline (mean ± threshold * stddev)."""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.history import HistoryStore


@dataclass
class AnomalyPolicy:
    """Configuration for anomaly detection."""
    min_samples: int = 5          # need at least this many runs to establish baseline
    threshold: float = 3.0        # number of stddevs that constitutes an anomaly

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be >= 2")
        if self.threshold <= 0:
            raise ValueError("threshold must be positive")


@dataclass
class AnomalyResult:
    job_name: str
    duration: float
    mean: float
    stddev: float
    is_anomaly: bool
    z_score: Optional[float] = None


@dataclass
class AnomalyDetector:
    store: HistoryStore
    policy: AnomalyPolicy = field(default_factory=AnomalyPolicy)

    def _durations(self, job_name: str) -> List[float]:
        """Return list of non-None durations for completed runs of *job_name*."""
        return [
            r.duration
            for r in self.store.read_for_job(job_name)
            if r.duration is not None
        ]

    def check(self, job_name: str, duration: float) -> AnomalyResult:
        """Check whether *duration* is anomalous for *job_name*."""
        durations = self._durations(job_name)

        if len(durations) < self.policy.min_samples:
            return AnomalyResult(
                job_name=job_name,
                duration=duration,
                mean=0.0,
                stddev=0.0,
                is_anomaly=False,
            )

        mean = statistics.mean(durations)
        stddev = statistics.pstdev(durations)  # population stddev

        if stddev == 0.0:
            z_score = 0.0
            is_anomaly = False
        else:
            z_score = abs(duration - mean) / stddev
            is_anomaly = z_score > self.policy.threshold

        return AnomalyResult(
            job_name=job_name,
            duration=duration,
            mean=mean,
            stddev=stddev,
            is_anomaly=is_anomaly,
            z_score=z_score,
        )

    def scan_all(self) -> Dict[str, List[AnomalyResult]]:
        """Scan every job in the store and return anomalous results grouped by job."""
        anomalies: Dict[str, List[AnomalyResult]] = {}
        jobs = {r.job_name for r in self.store.read_all()}
        for job in jobs:
            durations = self._durations(job)
            results = [self.check(job, d) for d in durations]
            flagged = [r for r in results if r.is_anomaly]
            if flagged:
                anomalies[job] = flagged
        return anomalies
