"""Tests for cronwatcher.trending."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwatcher.history import HistoryStore, ExecutionRecord
from cronwatcher.trending import TrendAnalyzer, TrendPolicy, TrendResult


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=offset_seconds
    )


def _rec(
    job: str, duration: float, ts: datetime | None = None, success: bool = True
) -> ExecutionRecord:
    return ExecutionRecord(
        job_name=job,
        timestamp=ts or _utc(),
        success=success,
        duration_seconds=duration,
        exit_code=0 if success else 1,
        notes=None,
    )


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(tmp_path)


def test_policy_rejects_min_samples_below_two() -> None:
    with pytest.raises(ValueError, match="min_samples"):
        TrendPolicy(min_samples=1)


def test_policy_rejects_non_positive_slope_threshold() -> None:
    with pytest.raises(ValueError, match="degradation_slope_threshold"):
        TrendPolicy(degradation_slope_threshold=0.0)


def test_returns_none_when_insufficient_samples(store: HistoryStore) -> None:
    for i in range(3):
        store.record(_rec("backup", duration=10.0, ts=_utc(i)))
    analyzer = TrendAnalyzer(store, TrendPolicy(min_samples=5))
    assert analyzer.analyze("backup") is None


def test_flat_trend_not_flagged(store: HistoryStore) -> None:
    for i in range(6):
        store.record(_rec("backup", duration=30.0, ts=_utc(i * 60)))
    analyzer = TrendAnalyzer(store)
    result = analyzer.analyze("backup")
    assert result is not None
    assert not result.is_degrading
    assert abs(result.slope) < 0.01


def test_increasing_trend_flagged(store: HistoryStore) -> None:
    # durations increase by 5s each run — well above default threshold of 1.0
    for i in range(8):
        store.record(_rec("etl", duration=float(10 + i * 5), ts=_utc(i * 60)))
    analyzer = TrendAnalyzer(store)
    result = analyzer.analyze("etl")
    assert result is not None
    assert result.is_degrading
    assert result.slope > 1.0


def test_str_representation(store: HistoryStore) -> None:
    for i in range(5):
        store.record(_rec("job_x", duration=float(20 + i), ts=_utc(i)))
    analyzer = TrendAnalyzer(store)
    result = analyzer.analyze("job_x")
    assert result is not None
    text = str(result)
    assert "job_x" in text
    assert "slope" in text


def test_analyze_all_sorted_by_slope(store: HistoryStore) -> None:
    for i in range(6):
        store.record(_rec("fast", duration=float(5 + i * 0.1), ts=_utc(i)))
        store.record(_rec("slow", duration=float(5 + i * 10), ts=_utc(i)))
    analyzer = TrendAnalyzer(store)
    results = analyzer.analyze_all(["fast", "slow"])
    assert len(results) == 2
    # highest slope first
    assert results[0].job_name == "slow"


def test_records_without_duration_ignored(store: HistoryStore) -> None:
    for i in range(4):
        store.record(_rec("nodur", duration=10.0, ts=_utc(i)))
    # add a record with no duration
    store.record(
        ExecutionRecord(
            job_name="nodur",
            timestamp=_utc(100),
            success=True,
            duration_seconds=None,
            exit_code=0,
            notes=None,
        )
    )
    analyzer = TrendAnalyzer(store, TrendPolicy(min_samples=5))
    # only 4 valid duration records — should return None
    assert analyzer.analyze("nodur") is None
