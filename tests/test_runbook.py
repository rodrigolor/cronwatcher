"""Tests for cronwatcher.runbook."""
from __future__ import annotations

import pytest

from cronwatcher.runbook import (
    RunbookEntry,
    RunbookRegistry,
    build_registry_from_config,
)


# ---------------------------------------------------------------------------
# RunbookEntry
# ---------------------------------------------------------------------------

def test_summary_url_and_notes():
    entry = RunbookEntry(job_name="backup", url="https://wiki/backup", notes="Check disk")
    summary = entry.summary()
    assert "backup" in summary
    assert "https://wiki/backup" in summary
    assert "Check disk" in summary


def test_summary_with_steps():
    entry = RunbookEntry(job_name="deploy", steps=["Pull latest", "Restart service"])
    summary = entry.summary()
    assert "1. Pull latest" in summary
    assert "2. Restart service" in summary


def test_summary_minimal():
    entry = RunbookEntry(job_name="noop")
    assert "noop" in entry.summary()


# ---------------------------------------------------------------------------
# RunbookRegistry
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> RunbookRegistry:
    return RunbookRegistry()


def test_register_and_get(registry: RunbookRegistry):
    entry = RunbookEntry(job_name="job1", notes="some note")
    registry.register(entry)
    assert registry.get("job1") is entry


def test_get_unknown_returns_none(registry: RunbookRegistry):
    assert registry.get("ghost") is None


def test_register_empty_name_raises(registry: RunbookRegistry):
    with pytest.raises(ValueError, match="job_name"):
        registry.register(RunbookEntry(job_name=""))


def test_register_overwrites(registry: RunbookRegistry):
    registry.register(RunbookEntry(job_name="j", notes="old"))
    registry.register(RunbookEntry(job_name="j", notes="new"))
    assert registry.get("j").notes == "new"  # type: ignore[union-attr]


def test_all_jobs_sorted(registry: RunbookRegistry):
    registry.register(RunbookEntry(job_name="z_job"))
    registry.register(RunbookEntry(job_name="a_job"))
    assert registry.all_jobs() == ["a_job", "z_job"]


def test_remove_existing(registry: RunbookRegistry):
    registry.register(RunbookEntry(job_name="temp"))
    assert registry.remove("temp") is True
    assert registry.get("temp") is None


def test_remove_nonexistent(registry: RunbookRegistry):
    assert registry.remove("ghost") is False


# ---------------------------------------------------------------------------
# build_registry_from_config
# ---------------------------------------------------------------------------

def test_build_from_config_populates_entries():
    jobs = [
        {"name": "backup", "runbook": {"url": "http://wiki/backup", "steps": ["do x"]}},
        {"name": "report", "runbook": None},
        {"name": "cleanup"},
    ]
    reg = build_registry_from_config(jobs)
    assert reg.get("backup") is not None
    assert reg.get("backup").url == "http://wiki/backup"  # type: ignore[union-attr]
    assert reg.get("report") is None
    assert reg.get("cleanup") is None
    assert reg.all_jobs() == ["backup"]


def test_build_from_empty_config():
    reg = build_registry_from_config([])
    assert reg.all_jobs() == []
