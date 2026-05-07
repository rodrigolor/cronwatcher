"""Execution forecast: predict next expected run times for registered jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from croniter import croniter

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import Scheduler


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ForecastEntry:
    job_name: str
    cron_expression: str
    next_run: datetime
    last_seen: Optional[datetime]
    overdue_by_seconds: float  # 0 if not yet overdue

    @property
    def is_overdue(self) -> bool:
        return self.overdue_by_seconds > 0

    def as_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "cron_expression": self.cron_expression,
            "next_run": self.next_run.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "overdue_by_seconds": round(self.overdue_by_seconds, 3),
            "is_overdue": self.is_overdue,
        }


class Forecaster:
    """Generates next-run forecasts for all registered jobs."""

    def __init__(self, jobs: List[JobConfig], scheduler: Scheduler) -> None:
        self._jobs = {j.name: j for j in jobs}
        self._scheduler = scheduler

    def forecast(self, now: Optional[datetime] = None) -> List[ForecastEntry]:
        """Return a sorted list of ForecastEntry objects (soonest first)."""
        if now is None:
            now = _utcnow()

        entries: List[ForecastEntry] = []
        for name, job in self._jobs.items():
            state = self._scheduler.state.get(name)
            last_seen = state.last_seen if state else None

            base = last_seen if last_seen else now
            cit = croniter(job.cron, base)
            next_run: datetime = cit.get_next(datetime)
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)

            overdue = max(0.0, (now - next_run).total_seconds())
            entries.append(
                ForecastEntry(
                    job_name=name,
                    cron_expression=job.cron,
                    next_run=next_run,
                    last_seen=last_seen,
                    overdue_by_seconds=overdue,
                )
            )

        entries.sort(key=lambda e: e.next_run)
        return entries
