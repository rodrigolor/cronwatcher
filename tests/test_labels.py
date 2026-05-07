"""Tests for cronwatcher.labels and cronwatcher.cli_labels."""
from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

from cronwatcher.labels import LabelStore
from cronwatcher import cli_labels


# ---------------------------------------------------------------------------
# LabelStore unit tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def store() -> LabelStore:
    return LabelStore()


def test_set_and_get(store: LabelStore) -> None:
    store.set("backup", "env", "prod")
    assert store.get("backup", "env") == "prod"


def test_get_missing_key_returns_none(store: LabelStore) -> None:
    assert store.get("backup", "missing") is None


def test_set_empty_job_raises(store: LabelStore) -> None:
    with pytest.raises(ValueError, match="job_name"):
        store.set("", "env", "prod")


def test_set_empty_key_raises(store: LabelStore) -> None:
    with pytest.raises(ValueError, match="label key"):
        store.set("backup", "", "prod")


def test_get_all_returns_copy(store: LabelStore) -> None:
    store.set("backup", "env", "prod")
    store.set("backup", "team", "ops")
    labels = store.get_all("backup")
    assert labels == {"env": "prod", "team": "ops"}


def test_get_all_unknown_job_returns_empty(store: LabelStore) -> None:
    assert store.get_all("unknown") == {}


def test_remove_existing_key(store: LabelStore) -> None:
    store.set("backup", "env", "prod")
    store.remove("backup", "env")
    assert store.get("backup", "env") is None


def test_remove_missing_key_is_noop(store: LabelStore) -> None:
    store.remove("backup", "nope")  # must not raise


def test_remove_all(store: LabelStore) -> None:
    store.set("backup", "env", "prod")
    store.remove_all("backup")
    assert store.get_all("backup") == {}


def test_jobs_with_label_key_only(store: LabelStore) -> None:
    store.set("backup", "env", "prod")
    store.set("cleanup", "env", "staging")
    store.set("report", "team", "ops")
    assert store.jobs_with_label("env") == ["backup", "cleanup"]


def test_jobs_with_label_key_and_value(store: LabelStore) -> None:
    store.set("backup", "env", "prod")
    store.set("cleanup", "env", "staging")
    assert store.jobs_with_label("env", "prod") == ["backup"]


def test_filter_jobs(store: LabelStore) -> None:
    store.set("backup", "env", "prod")
    store.set("cleanup", "env", "prod")
    result = store.filter_jobs(["backup", "report", "cleanup"], "env", "prod")
    assert result == ["backup", "cleanup"]


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

def _fresh_store() -> LabelStore:
    return LabelStore()


def _make_args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def test_cmd_set_prints_confirmation(capsys: pytest.CaptureFixture[str]) -> None:
    store = _fresh_store()
    with patch.object(cli_labels, "_build_store", return_value=store):
        cli_labels.cmd_labels_set(_make_args(job="backup", key="env", value="prod"))
    out = capsys.readouterr().out
    assert "env=prod" in out


def test_cmd_get_existing(capsys: pytest.CaptureFixture[str]) -> None:
    store = _fresh_store()
    store.set("backup", "env", "prod")
    with patch.object(cli_labels, "_build_store", return_value=store):
        cli_labels.cmd_labels_get(_make_args(job="backup", key="env"))
    assert "prod" in capsys.readouterr().out


def test_cmd_get_missing(capsys: pytest.CaptureFixture[str]) -> None:
    store = _fresh_store()
    with patch.object(cli_labels, "_build_store", return_value=store):
        cli_labels.cmd_labels_get(_make_args(job="backup", key="env"))
    assert "No label" in capsys.readouterr().out


def test_cmd_filter_no_match(capsys: pytest.CaptureFixture[str]) -> None:
    store = _fresh_store()
    with patch.object(cli_labels, "_build_store", return_value=store):
        cli_labels.cmd_labels_filter(_make_args(key="env", value=None))
    assert "No jobs" in capsys.readouterr().out


def test_build_labels_parser_registers_subcommand() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    cli_labels.build_labels_parser(sub)
    args = parser.parse_args(["labels", "set", "backup", "env", "prod"])
    assert args.job == "backup"
    assert args.key == "env"
    assert args.value == "prod"
