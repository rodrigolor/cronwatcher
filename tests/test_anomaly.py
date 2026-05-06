"""Tests for cronwatcher.anomaly."""
from __future__ import annotations

import datetime
import statistics
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatcher.anomaly import AnomalyDetector, AnomalyPolicy
from cronwatcher.history import ExecutionRecord, HistoryStore


def _utc(offset_seconds: float = 0) -> datetime.datetime:
    return datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc) + \
           datetime.timedelta(seconds=offset_seconds)


def _rec(job: str, duration: float, offset: float = 0) -> ExecutionRecord:
    return ExecutionRecord(
        job_name=job,
        started_at=_utc(offset),
        finished_at=_utc(offset + duration),
        success=True,
        exit_code=0,
        duration=duration,
    )


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(tmp_path)


# --- AnomalyPolicy validation ---

def test_policy_rejects_min_samples_below_two() -> None:
    with pytest.raises(ValueError, match="min_samples"):
        AnomalyPolicy(min_samples=1)


def test_policy_rejects_non_positive_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        AnomalyPolicy(threshold=0.0)


def test_policy_accepts_valid_values() -> None:
    p = AnomalyPolicy(min_samples=3, threshold=2.5)
    assert p.min_samples == 3
    assert p.threshold == 2.5


# --- AnomalyDetector.check ---

def test_no_anomaly_when_insufficient_samples(store: HistoryStore) -> None:
    for i in range(4):
        store.record(_rec("backup", 10.0, offset=float(i * 60)))
    detector = AnomalyDetector(store=store, policy=AnomalyPolicy(min_samples=5))
    result = detector.check("backup", 999.0)
    assert result.is_anomaly is False
    assert result.z_score is None


def test_anomaly_detected_for_outlier(store: HistoryStore) -> None:
    # 10 runs of ~10 s, then one run of 1000 s
    for i in range(10):
        store.record(_rec("backup", 10.0 + i * 0.1, offset=float(i * 60)))
    detector = AnomalyDetector(store=store, policy=AnomalyPolicy(min_samples=5, threshold=3.0))
    result = detector.check("backup", 1000.0)
    assert result.is_anomaly is True
    assert result.z_score is not None and result.z_score > 3.0


def test_normal_duration_not_flagged(store: HistoryStore) -> None:
    for i in range(10):
        store.record(_rec("sync", 20.0, offset=float(i * 60)))
    detector = AnomalyDetector(store=store)
    result = detector.check("sync", 20.5)
    assert result.is_anomaly is False


def test_zero_stddev_never_anomaly(store: HistoryStore) -> None:
    """All durations identical => stddev 0 => z-score 0 => never anomaly."""
    for i in range(6):
        store.record(_rec("clean", 5.0, offset=float(i * 60)))
    detector = AnomalyDetector(store=store)
    result = detector.check("clean", 5.0)
    assert result.is_anomaly is False
    assert result.z_score == 0.0


# --- AnomalyDetector.scan_all ---

def test_scan_all_returns_only_anomalous_jobs(store: HistoryStore) -> None:
    # job-a: stable
    for i in range(10):
        store.record(_rec("job-a", 10.0, offset=float(i * 60)))
    # job-b: one big outlier (we need it in history so scan_all picks it up)
    for i in range(9):
        store.record(_rec("job-b", 10.0, offset=float(i * 60)))
    store.record(_rec("job-b", 5000.0, offset=900.0))

    detector = AnomalyDetector(store=store, policy=AnomalyPolicy(min_samples=5, threshold=2.0))
    anomalies = detector.scan_all()
    assert "job-a" not in anomalies
    assert "job-b" in anomalies


def test_scan_all_empty_store(store: HistoryStore) -> None:
    detector = AnomalyDetector(store=store)
    assert detector.scan_all() == {}
