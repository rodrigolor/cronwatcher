"""Tests for cronwatcher.cli_trending."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_trending import build_trending_parser, cmd_trending
from cronwatcher.trending import TrendResult


def _make_args(**kwargs) -> argparse.Namespace:  # type: ignore[type-arg]
    defaults = dict(
        config="cronwatcher.yaml",
        history_dir=None,
        min_samples=5,
        slope_threshold=1.0,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _fake_result(name: str, degrading: bool = False) -> TrendResult:
    return TrendResult(
        job_name=name,
        sample_count=10,
        mean_duration=30.0,
        slope=2.5 if degrading else 0.1,
        is_degrading=degrading,
        latest_duration=35.0,
    )


@pytest.fixture()
def patched_analyzer():
    with patch("cronwatcher.cli_trending._build_analyzer") as mock:
        yield mock


def test_cmd_trending_no_data_prints_message(
    patched_analyzer: MagicMock, capsys: pytest.CaptureFixture
) -> None:
    patched_analyzer.return_value = (MagicMock(analyze_all=lambda _: []), ["job_a"])
    cmd_trending(_make_args())
    out = capsys.readouterr().out
    assert "insufficient" in out.lower() or "no trend" in out.lower()


def test_cmd_trending_shows_degrading_job(
    patched_analyzer: MagicMock, capsys: pytest.CaptureFixture
) -> None:
    results = [_fake_result("etl_job", degrading=True)]
    mock_a = MagicMock()
    mock_a.analyze_all.return_value = results
    patched_analyzer.return_value = (mock_a, ["etl_job"])
    cmd_trending(_make_args())
    out = capsys.readouterr().out
    assert "etl_job" in out
    assert "DEGRADING" in out


def test_cmd_trending_shows_ok_job(
    patched_analyzer: MagicMock, capsys: pytest.CaptureFixture
) -> None:
    results = [_fake_result("backup", degrading=False)]
    mock_a = MagicMock()
    mock_a.analyze_all.return_value = results
    patched_analyzer.return_value = (mock_a, ["backup"])
    cmd_trending(_make_args())
    out = capsys.readouterr().out
    assert "backup" in out
    assert "ok" in out


def test_build_trending_parser_registers_subcommand() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_trending_parser(sub)
    args = parser.parse_args(["trending", "--min-samples", "8"])
    assert args.min_samples == 8
    assert args.func is cmd_trending
