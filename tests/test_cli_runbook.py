"""Tests for cronwatcher.cli_runbook."""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_runbook import cmd_runbook_show
from cronwatcher.runbook import RunbookEntry, RunbookRegistry


def _make_args(job: str | None = None, config: str = "cronwatcher.yaml") -> MagicMock:
    args = MagicMock()
    args.config = config
    args.job = job
    return args


def _make_registry(*entries: RunbookEntry) -> RunbookRegistry:
    reg = RunbookRegistry()
    for e in entries:
        reg.register(e)
    return reg


@pytest.fixture()
def patched_registry(monkeypatch):
    """Patch _build_registry to return a controlled registry."""
    registry = _make_registry(
        RunbookEntry(job_name="alpha", notes="Check alpha logs"),
        RunbookEntry(job_name="beta", url="http://wiki/beta"),
    )

    def _fake_build(config):
        return registry

    monkeypatch.setattr("cronwatcher.cli_runbook._build_registry", _fake_build)
    monkeypatch.setattr(
        "cronwatcher.cli_runbook.CronWatcherConfig.from_file",
        lambda path: MagicMock(),
    )
    return registry


def test_show_all_jobs(patched_registry, capsys):
    rc = cmd_runbook_show(_make_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "alpha" in out
    assert "beta" in out


def test_show_specific_job(patched_registry, capsys):
    rc = cmd_runbook_show(_make_args(job="alpha"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "alpha" in out
    assert "Check alpha logs" in out
    assert "beta" not in out


def test_show_unknown_job_returns_error(patched_registry, capsys):
    rc = cmd_runbook_show(_make_args(job="ghost"))
    err = capsys.readouterr().err
    assert rc == 1
    assert "ghost" in err


def test_show_no_entries_prints_message(monkeypatch, capsys):
    monkeypatch.setattr(
        "cronwatcher.cli_runbook._build_registry",
        lambda _: RunbookRegistry(),
    )
    monkeypatch.setattr(
        "cronwatcher.cli_runbook.CronWatcherConfig.from_file",
        lambda path: MagicMock(),
    )
    rc = cmd_runbook_show(_make_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "No runbook" in out
