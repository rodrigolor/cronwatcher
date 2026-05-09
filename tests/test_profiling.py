"""Tests for cronwatcher.profiling."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatcher.history import ExecutionRecord, HistoryStore
from cronwatcher.profiling import DurationProfile, JobProfiler, ProfilingPolicy


def _utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def _rec(
    job: str,
    duration: float | None,
    ts: str = "2024-01-01T00:00:00",
    success: bool = True,
) -> ExecutionRecord:
    return ExecutionRecord(
        job_name=job,
        timestamp=_utc(ts),
        success=success,
        duration_seconds=duration,
    )


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    s = HistoryStore(str(tmp_path))
    for i in range(6):
        s.record(_rec("backup", float(10 + i)))
    return s


def test_policy_rejects_min_samples_below_two() -> None:
    with pytest.raises(ValueError, match="min_samples"):
        ProfilingPolicy(min_samples=1)


def test_profile_returns_none_with_too_few_samples(tmp_path: Path) -> None:
    s = HistoryStore(str(tmp_path))
    s.record(_rec("job", 5.0))
    profiler = JobProfiler(s, ProfilingPolicy(min_samples=5))
    assert profiler.profile("job") is None


def test_profile_returns_none_for_missing_job(store: HistoryStore) -> None:
    profiler = JobProfiler(store)
    assert profiler.profile("nonexistent") is None


def test_profile_computes_statistics(store: HistoryStore) -> None:
    profiler = JobProfiler(store)
    p = profiler.profile("backup")
    assert p is not None
    assert p.job_name == "backup"
    assert p.sample_count == 6
    assert p.min_seconds == pytest.approx(10.0)
    assert p.max_seconds == pytest.approx(15.0)
    assert p.mean_seconds == pytest.approx(12.5)


def test_profile_ignores_records_without_duration(tmp_path: Path) -> None:
    s = HistoryStore(str(tmp_path))
    for i in range(5):
        s.record(_rec("job", float(i + 1)))
    s.record(_rec("job", None))  # should be ignored
    profiler = JobProfiler(s, ProfilingPolicy(min_samples=5))
    p = profiler.profile("job")
    assert p is not None
    assert p.sample_count == 5


def test_profile_all_returns_only_sufficient_jobs(tmp_path: Path) -> None:
    s = HistoryStore(str(tmp_path))
    for i in range(6):
        s.record(_rec("good", float(i + 1)))
    s.record(_rec("sparse", 1.0))  # only 1 sample
    profiler = JobProfiler(s, ProfilingPolicy(min_samples=5))
    result = profiler.profile_all(["good", "sparse"])
    assert "good" in result
    assert "sparse" not in result


def test_duration_profile_str_contains_job_name(store: HistoryStore) -> None:
    profiler = JobProfiler(store)
    p = profiler.profile("backup")
    assert p is not None
    assert "backup" in str(p)
    assert "mean=" in str(p)
    assert "p95=" in str(p)


def test_p95_is_within_range(tmp_path: Path) -> None:
    s = HistoryStore(str(tmp_path))
    for i in range(20):
        s.record(_rec("job", float(i + 1)))
    profiler = JobProfiler(s, ProfilingPolicy(min_samples=5))
    p = profiler.profile("job")
    assert p is not None
    assert p.min_seconds <= p.p95_seconds <= p.max_seconds
