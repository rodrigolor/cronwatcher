"""Tests for cronwatcher.export."""
from __future__ import annotations

import csv
import io
import json
import pathlib
import tempfile
from datetime import datetime, timezone

import pytest

from cronwatcher.export import export_csv, export_history, export_json
from cronwatcher.history import ExecutionRecord, HistoryStore


def _ts(hour: int = 12) -> datetime:
    return datetime(2024, 1, 15, hour, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> HistoryStore:
    s = HistoryStore(tmp_path)
    s.record(ExecutionRecord("backup", _ts(10), True, 0, 5.2, ""))
    s.record(ExecutionRecord("backup", _ts(11), False, 1, 3.1, "error"))
    s.record(ExecutionRecord("cleanup", _ts(12), True, 0, 0.9, ""))
    return s


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------

def test_export_json_returns_valid_json(store: HistoryStore) -> None:
    result = export_history(store, fmt="json")
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) == 3


def test_export_json_fields_present(store: HistoryStore) -> None:
    data = json.loads(export_history(store, fmt="json"))
    keys = set(data[0].keys())
    assert keys == {"job_name", "timestamp", "success", "exit_code", "duration_seconds", "message"}


def test_export_json_filtered_by_job(store: HistoryStore) -> None:
    data = json.loads(export_history(store, fmt="json", job_name="backup"))
    assert len(data) == 2
    assert all(r["job_name"] == "backup" for r in data)


def test_export_json_empty_when_no_match(store: HistoryStore) -> None:
    data = json.loads(export_history(store, fmt="json", job_name="nonexistent"))
    assert data == []


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------

def test_export_csv_returns_string(store: HistoryStore) -> None:
    result = export_history(store, fmt="csv")
    assert isinstance(result, str)


def test_export_csv_has_header_and_rows(store: HistoryStore) -> None:
    result = export_history(store, fmt="csv")
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 3
    assert "job_name" in reader.fieldnames  # type: ignore[operator]


def test_export_csv_filtered_by_job(store: HistoryStore) -> None:
    result = export_history(store, fmt="csv", job_name="cleanup")
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["job_name"] == "cleanup"


def test_export_csv_success_field_serialised(store: HistoryStore) -> None:
    result = export_history(store, fmt="csv", job_name="backup")
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    success_values = {r["success"] for r in rows}
    assert success_values == {"True", "False"}
