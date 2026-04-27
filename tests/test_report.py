"""Tests for cronwatcher.report module."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

import pytest

from cronwatcher.history import ExecutionRecord, HistoryStore
from cronwatcher.report import JobSummary, Report, ReportGenerator


def _ts(hour: int = 12, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, 0, tzinfo=timezone.utc)


@pytest.fixture()
def store(tmp_path):
    return HistoryStore(str(tmp_path / "history"))


@pytest.fixture()
def generator(store):
    return ReportGenerator(store)


def test_empty_report_has_no_jobs(generator):
    report = generator.generate()
    assert report.jobs == {}


def test_report_counts_runs(store, generator):
    for i in range(3):
        store.record(ExecutionRecord("backup", _ts(hour=i), "success", exit_code=0, duration_seconds=1.0))
    store.record(ExecutionRecord("backup", _ts(hour=4), "failure", exit_code=1))

    report = generator.generate()
    summary = report.jobs["backup"]
    assert summary.total_runs == 4
    assert summary.successful_runs == 3
    assert summary.failed_runs == 1


def test_success_rate(store, generator):
    store.record(ExecutionRecord("job", _ts(), "success", exit_code=0))
    store.record(ExecutionRecord("job", _ts(hour=13), "success", exit_code=0))
    store.record(ExecutionRecord("job", _ts(hour=14), "failure", exit_code=1))

    summary = generator.generate().jobs["job"]
    assert abs(summary.success_rate - 66.666) < 0.1


def test_last_run_is_most_recent(store, generator):
    store.record(ExecutionRecord("job", _ts(hour=8), "success"))
    store.record(ExecutionRecord("job", _ts(hour=16), "failure"))
    store.record(ExecutionRecord("job", _ts(hour=12), "success"))

    summary = generator.generate().jobs["job"]
    assert summary.last_run == _ts(hour=16)
    assert summary.last_status == "failure"


def test_average_duration(store, generator):
    store.record(ExecutionRecord("job", _ts(), "success", duration_seconds=10.0))
    store.record(ExecutionRecord("job", _ts(hour=13), "success", duration_seconds=20.0))

    summary = generator.generate().jobs["job"]
    assert summary.average_duration_seconds == pytest.approx(15.0)


def test_average_duration_none_when_missing(store, generator):
    store.record(ExecutionRecord("job", _ts(), "success"))
    summary = generator.generate().jobs["job"]
    assert summary.average_duration_seconds is None


def test_generate_filters_by_job_names(store, generator):
    store.record(ExecutionRecord("alpha", _ts(), "success"))
    store.record(ExecutionRecord("beta", _ts(), "failure"))

    report = generator.generate(job_names=["alpha"])
    assert "alpha" in report.jobs
    assert "beta" not in report.jobs


def test_as_text_contains_job_name(store, generator):
    store.record(ExecutionRecord("nightly", _ts(), "success", duration_seconds=5.0))
    text = generator.generate().as_text()
    assert "nightly" in text
    assert "100.0%" in text


def test_as_text_no_history(generator):
    text = generator.generate().as_text()
    assert "No execution history" in text
