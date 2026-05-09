"""Tests for cronwatcher.cli_profiling."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_profiling import build_profiling_parser, cmd_profile
from cronwatcher.history import ExecutionRecord, HistoryStore
from cronwatcher.profiling import DurationProfile


def _utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def _make_args(**kwargs) -> argparse.Namespace:  # type: ignore[type-arg]
    defaults = {
        "history_dir": ".cronwatcher/history",
        "job": None,
        "min_samples": 5,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def populated_store(tmp_path: Path) -> HistoryStore:
    s = HistoryStore(str(tmp_path))
    for i in range(6):
        s.record(
            ExecutionRecord(
                job_name="nightly",
                timestamp=_utc(f"2024-01-0{i+1}T00:00:00"),
                success=True,
                duration_seconds=float(30 + i),
            )
        )
    return s


def test_build_profiling_parser_registers_subcommand() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_profiling_parser(sub)
    args = parser.parse_args(["profile", "--job", "backup"])
    assert args.job == "backup"


def test_cmd_profile_single_job_prints_output(
    tmp_path: Path, populated_store: HistoryStore, capsys: pytest.CaptureFixture
) -> None:
    args = _make_args(history_dir=str(tmp_path), job="nightly", min_samples=5)
    cmd_profile(args)
    out = capsys.readouterr().out
    assert "nightly" in out
    assert "mean=" in out


def test_cmd_profile_single_job_not_enough_samples(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    s = HistoryStore(str(tmp_path))
    s.record(
        ExecutionRecord(
            job_name="sparse",
            timestamp=_utc("2024-01-01T00:00:00"),
            success=True,
            duration_seconds=5.0,
        )
    )
    args = _make_args(history_dir=str(tmp_path), job="sparse", min_samples=5)
    cmd_profile(args)
    out = capsys.readouterr().out
    assert "Not enough samples" in out


def test_cmd_profile_all_jobs_no_data(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    args = _make_args(history_dir=str(tmp_path), job=None, min_samples=5)
    cmd_profile(args)
    out = capsys.readouterr().out
    assert "No profiling data" in out


def test_cmd_profile_all_jobs_shows_results(
    tmp_path: Path, populated_store: HistoryStore, capsys: pytest.CaptureFixture
) -> None:
    args = _make_args(history_dir=str(tmp_path), job=None, min_samples=5)
    cmd_profile(args)
    out = capsys.readouterr().out
    assert "nightly" in out
