"""Tests for cronwatcher.dashboard."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.dashboard import Dashboard, DashboardRow
from cronwatcher.history import HistoryStore, ExecutionRecord
from cronwatcher.scheduler import Scheduler


def _utc(offset_minutes: int = 0) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(minutes=offset_minutes)


@pytest.fixture()
def tmp_store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(str(tmp_path))


@pytest.fixture()
def scheduler() -> Scheduler:
    s = Scheduler()
    s.register(JobConfig(name="backup", schedule="0 2 * * *", grace_minutes=30))
    s.register(JobConfig(name="cleanup", schedule="*/5 * * * *", grace_minutes=10))
    return s


def test_no_jobs_renders_empty_message(tmp_store: HistoryStore) -> None:
    dash = Dashboard(Scheduler(), tmp_store)
    assert dash.render() == "No jobs registered.\n"


def test_rows_sorted_alphabetically(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    dash = Dashboard(scheduler, tmp_store)
    rows = dash.build_rows()
    names = [r.job_name for r in rows]
    assert names == sorted(names)


def test_unknown_status_when_no_history(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    dash = Dashboard(scheduler, tmp_store)
    rows = {r.job_name: r for r in dash.build_rows()}
    assert rows["backup"].status == "unknown"
    assert rows["cleanup"].status == "unknown"


def test_ok_status_after_successful_runs(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    for i in range(5):
        tmp_store.record(ExecutionRecord(job_name="backup", timestamp=_utc(i), success=True, duration=1.0))
    dash = Dashboard(scheduler, tmp_store)
    rows = {r.job_name: r for r in dash.build_rows()}
    assert rows["backup"].status == "ok"
    assert rows["backup"].total_runs == 5
    assert rows["backup"].success_rate == pytest.approx(1.0)


def test_failing_status_when_mostly_failures(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    for i in range(4):
        tmp_store.record(ExecutionRecord(job_name="cleanup", timestamp=_utc(i), success=False, duration=0.5))
    dash = Dashboard(scheduler, tmp_store)
    rows = {r.job_name: r for r in dash.build_rows()}
    assert rows["cleanup"].status == "failing"


def test_missed_status_overrides_history(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    tmp_store.record(ExecutionRecord(job_name="backup", timestamp=_utc(200), success=True, duration=1.0))
    scheduler.check_missed()  # last_seen is None, so missed flag set
    dash = Dashboard(scheduler, tmp_store)
    rows = {r.job_name: r for r in dash.build_rows()}
    assert rows["backup"].status == "missed"


def test_render_contains_job_names(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    output = Dashboard(scheduler, tmp_store).render()
    assert "backup" in output
    assert "cleanup" in output


def test_format_last_seen_never(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    dash = Dashboard(scheduler, tmp_store)
    rows = {r.job_name: r for r in dash.build_rows()}
    assert rows["backup"].format_last_seen() == "never"


def test_format_last_seen_minutes(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    row = DashboardRow(
        job_name="x",
        last_seen=_utc(offset_minutes=15),
        total_runs=1,
        success_rate=1.0,
        status="ok",
    )
    assert row.format_last_seen() == "15m ago"


def test_format_last_seen_hours(scheduler: Scheduler, tmp_store: HistoryStore) -> None:
    row = DashboardRow(
        job_name="x",
        last_seen=_utc(offset_minutes=130),
        total_runs=1,
        success_rate=1.0,
        status="ok",
    )
    assert row.format_last_seen() == "2h ago"
