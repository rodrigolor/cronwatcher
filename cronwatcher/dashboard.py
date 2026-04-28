"""Simple ASCII dashboard for cronwatcher status."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.history import HistoryStore
from cronwatcher.report import ReportGenerator, JobSummary
from cronwatcher.scheduler import Scheduler


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class DashboardRow:
    job_name: str
    last_seen: Optional[datetime]
    total_runs: int
    success_rate: float
    status: str  # "ok", "missed", "failing", "unknown"

    def format_last_seen(self) -> str:
        if self.last_seen is None:
            return "never"
        delta = _utcnow() - self.last_seen
        minutes = int(delta.total_seconds() // 60)
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        return f"{hours}h ago"


class Dashboard:
    """Builds a text dashboard from scheduler state and history."""

    def __init__(self, scheduler: Scheduler, store: HistoryStore) -> None:
        self._scheduler = scheduler
        self._generator = ReportGenerator(store)

    def build_rows(self) -> List[DashboardRow]:
        report = self._generator.generate()
        summary_map: dict[str, JobSummary] = {
            s.job_name: s for s in report.jobs
        }
        rows: List[DashboardRow] = []
        for name, state in self._scheduler.states.items():
            summary = summary_map.get(name)
            total = summary.total_runs if summary else 0
            rate = summary.success_rate if summary else 0.0
            if state.missed:
                status = "missed"
            elif total == 0:
                status = "unknown"
            elif rate < 0.5:
                status = "failing"
            else:
                status = "ok"
            rows.append(
                DashboardRow(
                    job_name=name,
                    last_seen=state.last_seen,
                    total_runs=total,
                    success_rate=rate,
                    status=status,
                )
            )
        return sorted(rows, key=lambda r: r.job_name)

    def render(self) -> str:
        rows = self.build_rows()
        if not rows:
            return "No jobs registered.\n"
        header = f"{'JOB':<30} {'LAST SEEN':<12} {'RUNS':>6} {'SUCCESS%':>9} {'STATUS':<10}"
        sep = "-" * len(header)
        lines = [header, sep]
        for r in rows:
            lines.append(
                f"{r.job_name:<30} {r.format_last_seen():<12} "
                f"{r.total_runs:>6} {r.success_rate * 100:>8.1f}% {r.status:<10}"
            )
        return "\n".join(lines) + "\n"
