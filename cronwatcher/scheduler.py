"""Schedule tracking and missed-run detection for cron jobs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from croniter import croniter

from cronwatcher.config import JobConfig

logger = logging.getLogger(__name__)


@dataclass
class JobState:
    """Tracks the last seen and expected execution times for a single job."""

    job: JobConfig
    last_seen: Optional[datetime] = None
    last_expected: Optional[datetime] = None
    missed_count: int = 0


@dataclass
class Scheduler:
    """Maintains state for all monitored jobs and detects missed runs."""

    jobs: Dict[str, JobState] = field(default_factory=dict)

    def register(self, job: JobConfig) -> None:
        """Register a job for tracking."""
        self.jobs[job.name] = JobState(job=job)
        logger.debug("Registered job '%s' with schedule '%s'", job.name, job.schedule)

    def record_execution(self, job_name: str, executed_at: Optional[datetime] = None) -> None:
        """Record a successful execution of a job."""
        if job_name not in self.jobs:
            raise KeyError(f"Unknown job: {job_name!r}")
        ts = executed_at or datetime.now(timezone.utc)
        state = self.jobs[job_name]
        state.last_seen = ts
        state.missed_count = 0
        logger.debug("Recorded execution of '%s' at %s", job_name, ts.isoformat())

    def check_missed(self, now: Optional[datetime] = None) -> list[str]:
        """Return names of jobs that missed their last expected run.

        A job is considered missed when the most recent expected fire time
        (according to its cron expression) is later than *last_seen*.
        """
        now = now or datetime.now(timezone.utc)
        missed: list[str] = []

        for name, state in self.jobs.items():
            cron = croniter(state.job.schedule, now)
            expected: datetime = cron.get_prev(datetime)  # type: ignore[arg-type]

            if expected == state.last_expected:
                # Already checked this interval
                continue

            state.last_expected = expected

            if state.last_seen is None or state.last_seen < expected:
                state.missed_count += 1
                logger.warning(
                    "Job '%s' missed expected run at %s (missed_count=%d)",
                    name,
                    expected.isoformat(),
                    state.missed_count,
                )
                missed.append(name)

        return missed
