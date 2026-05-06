"""Tests for cronwatcher.snapshots."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import Scheduler
from cronwatcher.snapshots import Snapshot, SnapshotEntry, SnapshotManager


def _utc(offset_seconds: int = 0) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path / "snapshots"


@pytest.fixture()
def scheduler() -> Scheduler:
    s = Scheduler()
    job = JobConfig(name="backup", schedule="* * * * *", command="/bin/backup")
    s.register(job)
    return s


def test_capture_creates_file(tmp_dir: Path, scheduler: Scheduler) -> None:
    manager = SnapshotManager(tmp_dir)
    snapshot = manager.capture(scheduler)
    files = list(tmp_dir.glob("snapshot_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["captured_at"] == snapshot.captured_at


def test_capture_includes_all_jobs(tmp_dir: Path, scheduler: Scheduler) -> None:
    manager = SnapshotManager(tmp_dir)
    snapshot = manager.capture(scheduler)
    names = [e.job_name for e in snapshot.entries]
    assert "backup" in names


def test_capture_marks_missed_job(tmp_dir: Path) -> None:
    s = Scheduler()
    job = JobConfig(name="hourly", schedule="0 * * * *", command="/bin/hourly")
    s.register(job)
    # Record execution 2 hours ago so it's stale
    s.record_execution("hourly", _utc(-7200))
    manager = SnapshotManager(tmp_dir)
    snapshot = manager.capture(s)
    entry = next(e for e in snapshot.entries if e.job_name == "hourly")
    assert entry.missed is True


def test_load_latest_returns_last_snapshot(tmp_dir: Path, scheduler: Scheduler) -> None:
    manager = SnapshotManager(tmp_dir)
    manager.capture(scheduler)
    manager.capture(scheduler)
    latest = manager.load_latest()
    assert latest is not None
    assert isinstance(latest, Snapshot)


def test_load_latest_returns_none_when_empty(tmp_dir: Path) -> None:
    manager = SnapshotManager(tmp_dir)
    assert manager.load_latest() is None


def test_list_snapshots_ordered(tmp_dir: Path, scheduler: Scheduler) -> None:
    manager = SnapshotManager(tmp_dir)
    manager.capture(scheduler)
    manager.capture(scheduler)
    files = manager.list_snapshots()
    assert len(files) == 2
    assert files[0].name < files[1].name


def test_diff_detects_missed_change(tmp_dir: Path) -> None:
    manager = SnapshotManager(tmp_dir)
    a = Snapshot(
        captured_at="2024-06-01T12:00:00+00:00",
        entries=[SnapshotEntry(job_name="db_backup", last_seen=None, missed=False)],
    )
    b = Snapshot(
        captured_at="2024-06-01T13:00:00+00:00",
        entries=[SnapshotEntry(job_name="db_backup", last_seen=None, missed=True)],
    )
    diff = manager.diff(a, b)
    assert "db_backup" in diff
    assert diff["db_backup"]["before"]["missed"] is False
    assert diff["db_backup"]["after"]["missed"] is True


def test_diff_no_changes_returns_empty(tmp_dir: Path) -> None:
    manager = SnapshotManager(tmp_dir)
    entry = SnapshotEntry(job_name="job", last_seen="2024-06-01T12:00:00+00:00", missed=False)
    a = Snapshot(captured_at="2024-06-01T12:00:00+00:00", entries=[entry])
    b = Snapshot(captured_at="2024-06-01T12:05:00+00:00", entries=[entry])
    assert manager.diff(a, b) == {}


def test_snapshot_roundtrip_via_dict() -> None:
    original = Snapshot(
        captured_at="2024-06-01T12:00:00+00:00",
        entries=[SnapshotEntry(job_name="x", last_seen=None, missed=True)],
    )
    restored = Snapshot.from_dict(original.as_dict())
    assert restored.captured_at == original.captured_at
    assert restored.entries[0].job_name == "x"
    assert restored.entries[0].missed is True
