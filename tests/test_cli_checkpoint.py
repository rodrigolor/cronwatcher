"""Tests for cronwatcher.cli_checkpoint CLI commands."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.checkpoint import CheckpointStore
from cronwatcher.cli_checkpoint import (
    build_checkpoint_parser,
    cmd_checkpoint_clear,
    cmd_checkpoint_list,
    cmd_checkpoint_show,
)


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _make_args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    defaults = {"checkpoint_file": str(tmp_path / "cp.json")}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_list_empty_prints_message(tmp_path: Path, capsys) -> None:
    args = _make_args(tmp_path)
    cmd_checkpoint_list(args)
    out = capsys.readouterr().out
    assert "No checkpoints" in out


def test_list_shows_entries(tmp_path: Path, capsys) -> None:
    store = CheckpointStore(tmp_path / "cp.json")
    store.record_success("backup", ts=_utc(2024, 1, 10))
    store.record_success("sync", ts=_utc(2024, 2, 5))
    args = _make_args(tmp_path)
    cmd_checkpoint_list(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "sync" in out


def test_show_existing_job(tmp_path: Path, capsys) -> None:
    store = CheckpointStore(tmp_path / "cp.json")
    store.record_success("nightly", ts=_utc(2024, 3, 1))
    args = _make_args(tmp_path, job="nightly")
    cmd_checkpoint_show(args)
    out = capsys.readouterr().out
    assert "nightly" in out
    assert "Run count" in out


def test_show_missing_job(tmp_path: Path, capsys) -> None:
    args = _make_args(tmp_path, job="ghost")
    cmd_checkpoint_show(args)
    out = capsys.readouterr().out
    assert "No checkpoint found" in out


def test_clear_existing_job(tmp_path: Path, capsys) -> None:
    store = CheckpointStore(tmp_path / "cp.json")
    store.record_success("cleanup", ts=_utc(2024, 4, 1))
    args = _make_args(tmp_path, job="cleanup")
    cmd_checkpoint_clear(args)
    out = capsys.readouterr().out
    assert "cleared" in out
    assert store.get("cleanup") is None


def test_clear_missing_job(tmp_path: Path, capsys) -> None:
    args = _make_args(tmp_path, job="nobody")
    cmd_checkpoint_clear(args)
    out = capsys.readouterr().out
    assert "No checkpoint found" in out


def test_build_checkpoint_parser_registers_subcommand() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_checkpoint_parser(sub)
    ns = parser.parse_args(["checkpoint", "list"])
    assert ns.cmd == "checkpoint"
    assert ns.checkpoint_cmd == "list"
