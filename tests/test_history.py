"""Tests for cronwatcher.history module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatcher.history import ExecutionRecord, HistoryStore


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(tmp_path / "history" / "exec.jsonl")


def test_record_creates_file(store: HistoryStore, tmp_path: Path) -> None:
    entry = ExecutionRecord.now("backup", success=True)
    store.record(entry)
    assert store._path.exists()


def test_record_appends_multiple(store: HistoryStore) -> None:
    store.record(ExecutionRecord.now("job1", success=True))
    store.record(ExecutionRecord.now("job1", success=False, exit_code=1))
    records = store.read_all()
    assert len(records) == 2


def test_read_all_empty_when_no_file(store: HistoryStore) -> None:
    assert store.read_all() == []


def test_read_for_job_filters_correctly(store: HistoryStore) -> None:
    store.record(ExecutionRecord.now("alpha", success=True))
    store.record(ExecutionRecord.now("beta", success=False))
    store.record(ExecutionRecord.now("alpha", success=True))

    alpha_records = store.read_for_job("alpha")
    assert len(alpha_records) == 2
    assert all(r.job_name == "alpha" for r in alpha_records)


def test_last_success_returns_most_recent(store: HistoryStore) -> None:
    store.record(ExecutionRecord.now("myjob", success=True, message="first"))
    store.record(ExecutionRecord.now("myjob", success=False, exit_code=2))
    store.record(ExecutionRecord.now("myjob", success=True, message="second"))

    rec = store.last_success("myjob")
    assert rec is not None
    assert rec.message == "second"


def test_last_success_none_when_all_failed(store: HistoryStore) -> None:
    store.record(ExecutionRecord.now("myjob", success=False, exit_code=1))
    assert store.last_success("myjob") is None


def test_last_success_none_for_unknown_job(store: HistoryStore) -> None:
    assert store.last_success("nonexistent") is None


def test_record_fields_persisted(store: HistoryStore) -> None:
    entry = ExecutionRecord.now("deploy", success=False, exit_code=127, message="cmd not found")
    store.record(entry)
    records = store.read_all()
    assert len(records) == 1
    r = records[0]
    assert r.job_name == "deploy"
    assert r.success is False
    assert r.exit_code == 127
    assert r.message == "cmd not found"


def test_clear_removes_file(store: HistoryStore) -> None:
    store.record(ExecutionRecord.now("x", success=True))
    store.clear()
    assert not store._path.exists()
    assert store.read_all() == []


def test_execution_record_now_has_iso_timestamp(store: HistoryStore) -> None:
    rec = ExecutionRecord.now("ts_job", success=True)
    # Should parse without error
    from datetime import datetime
    dt = datetime.fromisoformat(rec.timestamp)
    assert dt.tzinfo is not None
