"""Tests for cronwatcher.audit and cronwatcher.cli_audit."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatcher.audit import AuditEvent, AuditLog
from cronwatcher.cli_audit import build_audit_parser, cmd_audit_list


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


@pytest.fixture()
def log(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path)


# ---------------------------------------------------------------------------
# AuditEvent
# ---------------------------------------------------------------------------

def test_event_as_dict_contains_all_fields() -> None:
    ev = AuditEvent("job_missed", "backup", "no ping in 10 min", _utc(2024, 1, 1))
    d = ev.as_dict()
    assert d["event_type"] == "job_missed"
    assert d["job_name"] == "backup"
    assert d["detail"] == "no ping in 10 min"
    assert "2024-01-01" in d["timestamp"]


def test_event_job_name_may_be_none() -> None:
    ev = AuditEvent("system_start", None, "daemon started")
    assert ev.as_dict()["job_name"] is None


# ---------------------------------------------------------------------------
# AuditLog.record / read_all
# ---------------------------------------------------------------------------

def test_record_creates_file(log: AuditLog, tmp_path: Path) -> None:
    log.record(AuditEvent("job_missed", "nightly", "missed"))
    assert (tmp_path / "audit.jsonl").exists()


def test_read_all_empty_when_no_file(log: AuditLog) -> None:
    assert log.read_all() == []


def test_record_and_read_roundtrip(log: AuditLog) -> None:
    log.record(AuditEvent("alert_sent", "deploy", "email sent", _utc(2024, 3, 5)))
    log.record(AuditEvent("job_failure", "cleanup", "exit 1", _utc(2024, 3, 6)))
    events = log.read_all()
    assert len(events) == 2
    assert events[0].event_type == "alert_sent"
    assert events[1].job_name == "cleanup"


def test_read_for_job_filters(log: AuditLog) -> None:
    log.record(AuditEvent("job_missed", "backup", "missed"))
    log.record(AuditEvent("job_missed", "deploy", "missed"))
    log.record(AuditEvent("alert_sent", "backup", "sent"))
    result = log.read_for_job("backup")
    assert len(result) == 2
    assert all(e.job_name == "backup" for e in result)


def test_read_by_type_filters(log: AuditLog) -> None:
    log.record(AuditEvent("job_missed", "a", "x"))
    log.record(AuditEvent("alert_sent", "a", "y"))
    log.record(AuditEvent("alert_sent", "b", "z"))
    result = log.read_by_type("alert_sent")
    assert len(result) == 2
    assert all(e.event_type == "alert_sent" for e in result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _make_args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    defaults = {"log_dir": str(tmp_path), "job": None, "event_type": None, "last": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cli_no_events_prints_message(tmp_path: Path, capsys) -> None:
    cmd_audit_list(_make_args(tmp_path))
    out = capsys.readouterr().out
    assert "No audit events" in out


def test_cli_lists_events(tmp_path: Path, capsys) -> None:
    log = AuditLog(tmp_path)
    log.record(AuditEvent("job_missed", "nightly", "no heartbeat", _utc(2024, 5, 1)))
    cmd_audit_list(_make_args(tmp_path))
    out = capsys.readouterr().out
    assert "job_missed" in out
    assert "nightly" in out


def test_cli_last_limits_output(tmp_path: Path, capsys) -> None:
    log = AuditLog(tmp_path)
    for i in range(5):
        log.record(AuditEvent("job_missed", f"job{i}", "x"))
    cmd_audit_list(_make_args(tmp_path, last=2))
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if "job_missed" in l]
    assert len(lines) == 2


def test_build_audit_parser_registers_subcommand() -> None:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()
    build_audit_parser(subs)
    args = parser.parse_args(["audit", "--last", "5"])
    assert args.last == 5
    assert args.func is cmd_audit_list
