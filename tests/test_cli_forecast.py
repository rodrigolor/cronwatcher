"""Tests for cronwatcher.cli_forecast."""

from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_forecast import cmd_forecast, build_forecast_parser
from cronwatcher.forecast import ForecastEntry
from datetime import datetime, timezone


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"config": "cronwatcher.yaml", "format": "text"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _fake_entry(name: str = "backup", overdue: float = 0.0) -> ForecastEntry:
    return ForecastEntry(
        job_name=name,
        cron_expression="* * * * *",
        next_run=datetime(2024, 1, 15, 12, 1, 0, tzinfo=timezone.utc),
        last_seen=None,
        overdue_by_seconds=overdue,
    )


@pytest.fixture()
def patched_forecast(monkeypatch):
    entries = [_fake_entry("backup"), _fake_entry("cleanup", overdue=120.0)]

    def _fake_cmd(args):
        from cronwatcher.cli_forecast import _render_text
        if args.format == "json":
            print(json.dumps([e.as_dict() for e in entries], indent=2))
        else:
            print(_render_text(entries))

    return _fake_cmd, entries


def test_build_forecast_parser_registers_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_forecast_parser(sub)
    args = parser.parse_args(["forecast", "--format", "json"])
    assert args.format == "json"


def test_cmd_forecast_text_output(capsys, tmp_path, monkeypatch):
    from cronwatcher.cli_forecast import _render_text
    entries = [_fake_entry("backup")]
    output = _render_text(entries)
    assert "backup" in output
    assert "NEXT RUN" in output


def test_render_text_marks_overdue():
    from cronwatcher.cli_forecast import _render_text
    entries = [_fake_entry("slow_job", overdue=300.0)]
    output = _render_text(entries)
    assert "YES" in output
    assert "300" in output


def test_render_text_no_jobs():
    from cronwatcher.cli_forecast import _render_text
    assert _render_text([]) == "No jobs registered."


def test_cmd_forecast_json_output(capsys, tmp_path, monkeypatch):
    from cronwatcher.config import CronWatcherConfig, JobConfig, AlertConfig
    from cronwatcher.scheduler import Scheduler
    from cronwatcher import cli_forecast

    job = JobConfig(name="nightly", cron="0 2 * * *", grace_seconds=300)
    cfg = MagicMock(spec=CronWatcherConfig)
    cfg.jobs = [job]

    monkeypatch.setattr(cli_forecast.CronWatcherConfig, "from_file", lambda p: cfg)

    args = _make_args(format="json")
    cmd_forecast(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert data[0]["job_name"] == "nightly"
