"""Tests for cronwatcher.cli module."""

from __future__ import annotations

import textwrap
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.history import HistoryStore, ExecutionRecord
from cronwatcher.cli import main


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "cronwatcher.yaml"
    cfg.write_text(
        textwrap.dedent(
            f"""\
            history_dir: {tmp_path / 'history'}
            retention_days: 30
            jobs:
              - name: test_job
                schedule: "* * * * *"
            alerts:
              enabled: false
            """
        )
    )
    return cfg


@pytest.fixture
def store_with_records(tmp_path: Path, config_file: Path) -> HistoryStore:
    store = HistoryStore(str(tmp_path / "history"))
    now = datetime.now(tz=timezone.utc)
    store.record(
        ExecutionRecord("test_job", now - timedelta(days=40), True, 0, "old")
    )
    store.record(
        ExecutionRecord("test_job", now - timedelta(days=2), True, 0, "fresh")
    )
    return store


def test_prune_removes_old_records(tmp_path, config_file, store_with_records):
    result = main(["prune", "--config", str(config_file)])
    assert result == 0
    remaining = store_with_records.read_for_job("test_job")
    assert len(remaining) == 1
    assert remaining[0].message == "fresh"


def test_prune_dry_run_does_not_delete(tmp_path, config_file, store_with_records, capsys):
    result = main(["prune", "--config", str(config_file), "--dry-run"])
    assert result == 0
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "1" in out
    # Records should still be there
    assert len(store_with_records.read_for_job("test_job")) == 2


def test_prune_max_age_override(tmp_path, config_file, store_with_records):
    # Override to 1 day — both records older than 1 day should be removed
    result = main(["prune", "--config", str(config_file), "--max-age-days", "1"])
    assert result == 0
    remaining = store_with_records.read_for_job("test_job")
    assert len(remaining) == 0


def test_no_command_prints_help_returns_nonzero(capsys):
    result = main([])
    assert result == 1


def test_prune_missing_config_returns_nonzero(tmp_path):
    """Prune should return a non-zero exit code when the config file does not exist."""
    nonexistent = tmp_path / "does_not_exist.yaml"
    result = main(["prune", "--config", str(nonexistent)])
    assert result != 0
