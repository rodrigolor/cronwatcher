"""Notifier decorator that logs a warning when a job's duration is anomalous."""
from __future__ import annotations

import logging
from typing import Optional

from cronwatcher.history import HistoryStore
from cronwatcher.notifier import Notifier
from cronwatcher.profiling import JobProfiler, ProfilingPolicy

logger = logging.getLogger(__name__)

_DEFAULT_SLOW_FACTOR = 2.0  # alert when duration > mean * factor


class ProfilingNotifier:
    """Wraps a Notifier and emits a warning when job duration exceeds the profiled mean."""

    def __init__(
        self,
        inner: Notifier,
        store: HistoryStore,
        slow_factor: float = _DEFAULT_SLOW_FACTOR,
        policy: Optional[ProfilingPolicy] = None,
    ) -> None:
        if slow_factor <= 0:
            raise ValueError("slow_factor must be positive")
        self._inner = inner
        self._profiler = JobProfiler(store, policy or ProfilingPolicy())
        self._slow_factor = slow_factor

    def notify_missed(self, job_name: str) -> None:
        self._inner.notify_missed(job_name)

    def notify_failure(
        self,
        job_name: str,
        exit_code: Optional[int] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        self._inner.notify_failure(job_name, exit_code=exit_code, duration_seconds=duration_seconds)
        if duration_seconds is not None:
            self._check_slow(job_name, duration_seconds)

    def recover(self, job_name: str) -> None:
        if hasattr(self._inner, "recover"):
            self._inner.recover(job_name)  # type: ignore[attr-defined]

    def _check_slow(self, job_name: str, duration_seconds: float) -> None:
        profile = self._profiler.profile(job_name)
        if profile is None:
            return
        threshold = profile.mean_seconds * self._slow_factor
        if duration_seconds > threshold:
            logger.warning(
                "Slow execution detected for '%s': %.2fs exceeds %.1fx mean (%.2fs)",
                job_name,
                duration_seconds,
                self._slow_factor,
                profile.mean_seconds,
            )
