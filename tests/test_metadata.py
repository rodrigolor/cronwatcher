"""Tests for cronwatcher.metadata and cronwatcher.cli_metadata."""
from __future__ import annotations

import argparse
import pytest

from cronwatcher.metadata import JobMetadata, MetadataStore
from cronwatcher.cli_metadata import (
    cmd_metadata_get,
    cmd_metadata_remove,
    cmd_metadata_set,
    cmd_metadata_show,
    build_metadata_parser,
)


# ---------------------------------------------------------------------------
# JobMetadata unit tests
# ---------------------------------------------------------------------------

def test_set_and_get():
    m = JobMetadata(job_name="backup")
    m.set("owner", "alice")
    assert m.get("owner") == "alice"


def test_get_missing_key_returns_none():
    m = JobMetadata(job_name="backup")
    assert m.get("nonexistent") is None


def test_set_empty_key_raises():
    m = JobMetadata(job_name="backup")
    with pytest.raises(ValueError, match="empty"):
        m.set("", "value")


def test_remove_existing_key():
    m = JobMetadata(job_name="backup")
    m.set("env", "prod")
    m.remove("env")
    assert m.get("env") is None


def test_remove_missing_key_is_noop():
    m = JobMetadata(job_name="backup")
    m.remove("ghost")  # should not raise


def test_as_dict_structure():
    m = JobMetadata(job_name="sync", annotations={"team": "ops"})
    d = m.as_dict()
    assert d["job_name"] == "sync"
    assert d["annotations"] == {"team": "ops"}


# ---------------------------------------------------------------------------
# MetadataStore tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    return MetadataStore(directory=str(tmp_path / "meta"))


def test_load_unknown_job_returns_empty(store):
    meta = store.load("unknown")
    assert meta.job_name == "unknown"
    assert meta.annotations == {}


def test_save_and_load_roundtrip(store):
    meta = store.load("deploy")
    meta.set("team", "platform")
    meta.set("env", "staging")
    store.save(meta)

    loaded = store.load("deploy")
    assert loaded.get("team") == "platform"
    assert loaded.get("env") == "staging"


def test_all_jobs_lists_saved_jobs(store):
    for name in ("alpha", "beta", "gamma"):
        m = store.load(name)
        m.set("k", "v")
        store.save(m)
    assert set(store.all_jobs()) == {"alpha", "beta", "gamma"}


def test_delete_removes_job(store):
    m = store.load("temp")
    m.set("x", "y")
    store.save(m)
    store.delete("temp")
    assert "temp" not in store.all_jobs()


def test_delete_nonexistent_is_noop(store):
    store.delete("ghost")  # should not raise


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------

def _args(tmp_path, **kwargs) -> argparse.Namespace:
    base = argparse.Namespace(data_dir=str(tmp_path / "meta"))
    for k, v in kwargs.items():
        setattr(base, k, v)
    return base


def test_cmd_set_and_show(tmp_path, capsys):
    cmd_metadata_set(_args(tmp_path, job="report", key="owner", value="bob"))
    cmd_metadata_show(_args(tmp_path, job="report"))
    out = capsys.readouterr().out
    assert "owner" in out
    assert "bob" in out


def test_cmd_get_existing_key(tmp_path, capsys):
    cmd_metadata_set(_args(tmp_path, job="job1", key="env", value="prod"))
    cmd_metadata_get(_args(tmp_path, job="job1", key="env"))
    assert "prod" in capsys.readouterr().out


def test_cmd_get_missing_key_exits(tmp_path):
    with pytest.raises(SystemExit):
        cmd_metadata_get(_args(tmp_path, job="job1", key="missing"))


def test_cmd_remove_key(tmp_path, capsys):
    cmd_metadata_set(_args(tmp_path, job="job2", key="tier", value="gold"))
    cmd_metadata_remove(_args(tmp_path, job="job2", key="tier"))
    with pytest.raises(SystemExit):
        cmd_metadata_get(_args(tmp_path, job="job2", key="tier"))


def test_build_metadata_parser_registers_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_metadata_parser(sub)
    args = parser.parse_args(["metadata", "show", "myjob"])
    assert args.job == "myjob"
