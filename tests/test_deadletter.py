"""Tests for the dead-letter queue and DeadLetterNotifier."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from cronwatcher.deadletter import DeadLetter, DeadLetterQueue
from cronwatcher.notifier_deadletter import DeadLetterNotifier


def _utc(year=2024, month=1, day=1, hour=0, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def queue(tmp_path):
    return DeadLetterQueue(str(tmp_path / "dlq" / "queue.jsonl"))


# --- DeadLetter dataclass ---

def test_as_dict_contains_all_fields():
    dl = DeadLetter(job_name="backup", alert_type="missed", message="Missed!",
                    created_at=_utc(), attempts=2)
    d = dl.as_dict()
    assert d["job_name"] == "backup"
    assert d["alert_type"] == "missed"
    assert d["message"] == "Missed!"
    assert d["attempts"] == 2
    assert "created_at" in d


def test_from_dict_roundtrip():
    dl = DeadLetter(job_name="sync", alert_type="failure", message="Exit 1",
                    created_at=_utc(2024, 3, 5), attempts=1)
    restored = DeadLetter.from_dict(dl.as_dict())
    assert restored.job_name == dl.job_name
    assert restored.alert_type == dl.alert_type
    assert restored.attempts == dl.attempts


# --- DeadLetterQueue ---

def test_push_and_read_all(queue):
    dl = DeadLetter(job_name="job1", alert_type="missed", message="m")
    queue.push(dl)
    letters = queue.read_all()
    assert len(letters) == 1
    assert letters[0].job_name == "job1"


def test_read_all_empty_when_no_file(queue):
    assert queue.read_all() == []


def test_push_multiple_appends(queue):
    queue.push(DeadLetter("a", "missed", "m1"))
    queue.push(DeadLetter("b", "failure", "m2"))
    assert len(queue.read_all()) == 2


def test_clear_removes_all(queue):
    queue.push(DeadLetter("a", "missed", "m"))
    queue.clear()
    assert queue.read_all() == []


def test_rewrite_replaces_contents(queue):
    queue.push(DeadLetter("old", "missed", "m"))
    new_letters = [DeadLetter("new", "failure", "f")]
    queue.rewrite(new_letters)
    result = queue.read_all()
    assert len(result) == 1
    assert result[0].job_name == "new"


# --- DeadLetterNotifier ---

def test_notify_missed_delegates_to_inner(queue):
    inner = MagicMock()
    dn = DeadLetterNotifier(inner, queue)
    dn.notify_missed("myjob")
    inner.notify_missed.assert_called_once_with("myjob")
    assert queue.read_all() == []


def test_notify_missed_enqueues_on_failure(queue):
    inner = MagicMock()
    inner.notify_missed.side_effect = RuntimeError("smtp down")
    dn = DeadLetterNotifier(inner, queue)
    dn.notify_missed("myjob")
    letters = queue.read_all()
    assert len(letters) == 1
    assert letters[0].alert_type == "missed"


def test_notify_failure_enqueues_on_failure(queue):
    inner = MagicMock()
    inner.notify_failure.side_effect = ConnectionError("timeout")
    dn = DeadLetterNotifier(inner, queue)
    dn.notify_failure("myjob", exit_code=1)
    letters = queue.read_all()
    assert len(letters) == 1
    assert letters[0].alert_type == "failure"


def test_replay_clears_queue_on_success(queue):
    queue.push(DeadLetter("j", "missed", "m"))
    inner = MagicMock()
    dn = DeadLetterNotifier(inner, queue)
    replayed = dn.replay()
    assert replayed == 1
    assert queue.read_all() == []


def test_replay_drops_after_max_attempts(queue):
    dl = DeadLetter("j", "missed", "m", attempts=3)
    queue.push(dl)
    inner = MagicMock()
    dn = DeadLetterNotifier(inner, queue)
    replayed = dn.replay(max_attempts=3)
    assert replayed == 0
    assert queue.read_all() == []
