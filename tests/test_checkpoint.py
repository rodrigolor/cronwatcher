"""Tests for cronwatcher.checkpoint."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatcher.checkpoint import CheckpointEntry, CheckpointStore


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(tmp_path / "checkpoints.json")


def test_get_missing_returns_none(store: CheckpointStore) -> None:
    assert store.get("backup") is None


def test_record_success_creates_entry(store: CheckpointStore) -> None:
    ts = _utc(2024, 1, 10, 8, 0)
    entry = store.record_success("backup", ts=ts)
    assert entry.job_name == "backup"
    assert entry.last_success == ts
    assert entry.run_count == 1


def test_record_success_increments_run_count(store: CheckpointStore) -> None:
    ts1 = _utc(2024, 1, 10, 8, 0)
    ts2 = _utc(2024, 1, 10, 9, 0)
    store.record_success("backup", ts=ts1)
    entry = store.record_success("backup", ts=ts2)
    assert entry.run_count == 2
    assert entry.last_success == ts2


def test_get_returns_persisted_entry(store: CheckpointStore) -> None:
    ts = _utc(2024, 3, 1, 12, 0)
    store.record_success("cleanup", ts=ts)
    fetched = store.get("cleanup")
    assert fetched is not None
    assert fetched.last_success == ts
    assert fetched.run_count == 1


def test_all_entries_sorted_by_name(store: CheckpointStore) -> None:
    store.record_success("zebra", ts=_utc(2024, 1, 1))
    store.record_success("alpha", ts=_utc(2024, 1, 2))
    store.record_success("middle", ts=_utc(2024, 1, 3))
    names = [e.job_name for e in store.all_entries()]
    assert names == ["alpha", "middle", "zebra"]


def test_all_entries_empty_when_no_file(store: CheckpointStore) -> None:
    assert store.all_entries() == []


def test_clear_removes_entry(store: CheckpointStore) -> None:
    store.record_success("sync", ts=_utc(2024, 5, 1))
    removed = store.clear("sync")
    assert removed is True
    assert store.get("sync") is None


def test_clear_nonexistent_returns_false(store: CheckpointStore) -> None:
    assert store.clear("ghost") is False


def test_record_empty_job_name_raises(store: CheckpointStore) -> None:
    with pytest.raises(ValueError):
        store.record_success("", ts=_utc(2024, 1, 1))


def test_as_dict_roundtrip() -> None:
    ts = _utc(2024, 6, 15, 10, 30)
    entry = CheckpointEntry(job_name="nightly", last_success=ts, run_count=7)
    restored = CheckpointEntry.from_dict(entry.as_dict())
    assert restored.job_name == entry.job_name
    assert restored.last_success == entry.last_success
    assert restored.run_count == entry.run_count


def test_record_success_defaults_to_now(store: CheckpointStore) -> None:
    """Calling record_success without ts should not raise and should set a recent timestamp."""
    from datetime import timedelta
    before = datetime.now(timezone.utc) - timedelta(seconds=2)
    entry = store.record_success("auto_ts")
    assert entry.last_success >= before
