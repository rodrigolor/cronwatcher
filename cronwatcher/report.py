"""Generates summary reports from execution history."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatcher.history import ExecutionRecord, HistoryStore


@dataclass
class JobSummary:
    job_name: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    average_duration_seconds: Optional[float] = None

    @property
    def success_rate(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.successful_runs / self.total_runs * 100


@dataclass
class Report:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    jobs: Dict[str, JobSummary] = field(default_factory=dict)

    def as_text(self) -> str:
        lines = [
            f"CronWatcher Report — {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "=" * 60,
        ]
        if not self.jobs:
            lines.append("No execution history found.")
            return "\n".join(lines)
        for name, summary in sorted(self.jobs.items()):
            rate = f"{summary.success_rate:.1f}%" if summary.success_rate is not None else "N/A"
            last = summary.last_run.strftime("%Y-%m-%d %H:%M:%S UTC") if summary.last_run else "never"
            avg = f"{summary.average_duration_seconds:.2f}s" if summary.average_duration_seconds is not None else "N/A"
            lines += [
                f"  Job: {name}",
                f"    Runs: {summary.total_runs}  OK: {summary.successful_runs}  FAIL: {summary.failed_runs}  Success rate: {rate}",
                f"    Last run: {last}  Status: {summary.last_status or 'N/A'}  Avg duration: {avg}",
            ]
        return "\n".join(lines)

    def failing_jobs(self) -> List[JobSummary]:
        """Return summaries for jobs whose last run did not succeed."""
        return [
            summary
            for summary in self.jobs.values()
            if summary.last_status is not None and summary.last_status != "success"
        ]


class ReportGenerator:
    def __init__(self, store: HistoryStore) -> None:
        self._store = store

    def generate(self, job_names: Optional[List[str]] = None) -> Report:
        report = Report()
        names = job_names if job_names is not None else self._store.list_jobs()
        for name in names:
            records: List[ExecutionRecord] = self._store.read_for_job(name)
            summary = JobSummary(job_name=name, total_runs=len(records))
            durations: List[float] = []
            for rec in records:
                if rec.status == "success":
                    summary.successful_runs += 1
                else:
                    summary.failed_runs += 1
                if summary.last_run is None or rec.timestamp > summary.last_run:
                    summary.last_run = rec.timestamp
                    summary.last_status = rec.status
                if rec.duration_seconds is not None:
                    durations.append(rec.duration_seconds)
            if durations:
                summary.average_duration_seconds = sum(durations) / len(durations)
            report.jobs[name] = summary
        return report
