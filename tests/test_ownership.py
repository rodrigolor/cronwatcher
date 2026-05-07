"""Tests for cronwatcher.ownership."""
import pytest

from cronwatcher.ownership import OwnershipRegistry


@pytest.fixture
def registry() -> OwnershipRegistry:
    return OwnershipRegistry()


def test_register_and_get(registry):
    registry.register("backup", "alice", email="alice@example.com", team="ops")
    entry = registry.get("backup")
    assert entry is not None
    assert entry.job_name == "backup"
    assert entry.owner == "alice"
    assert entry.email == "alice@example.com"
    assert entry.team == "ops"


def test_get_unknown_job_returns_none(registry):
    assert registry.get("nonexistent") is None


def test_register_empty_job_name_raises(registry):
    with pytest.raises(ValueError, match="job_name"):
        registry.register("", "alice")


def test_register_empty_owner_raises(registry):
    with pytest.raises(ValueError, match="owner"):
        registry.register("backup", "")


def test_register_overwrites_previous_entry(registry):
    registry.register("backup", "alice")
    registry.register("backup", "bob", team="infra")
    entry = registry.get("backup")
    assert entry.owner == "bob"
    assert entry.team == "infra"


def test_remove_existing_entry(registry):
    registry.register("backup", "alice")
    registry.remove("backup")
    assert registry.get("backup") is None


def test_remove_missing_entry_is_noop(registry):
    registry.remove("ghost")  # should not raise


def test_all_entries_sorted_alphabetically(registry):
    registry.register("zebra_job", "carol")
    registry.register("alpha_job", "dave")
    registry.register("middle_job", "eve")
    names = [e.job_name for e in registry.all_entries()]
    assert names == ["alpha_job", "middle_job", "zebra_job"]


def test_jobs_for_team(registry):
    registry.register("job_a", "alice", team="ops")
    registry.register("job_b", "bob", team="dev")
    registry.register("job_c", "carol", team="ops")
    assert sorted(registry.jobs_for_team("ops")) == ["job_a", "job_c"]


def test_jobs_for_unknown_team_returns_empty(registry):
    registry.register("job_a", "alice", team="ops")
    assert registry.jobs_for_team("nonexistent") == []


def test_jobs_for_owner(registry):
    registry.register("job_a", "alice")
    registry.register("job_b", "bob")
    registry.register("job_c", "alice")
    assert sorted(registry.jobs_for_owner("alice")) == ["job_a", "job_c"]


def test_as_dict_contains_all_fields(registry):
    registry.register("report", "alice", email="a@x.com", team="ops", notes="critical")
    d = registry.get("report").as_dict()
    assert d["job_name"] == "report"
    assert d["owner"] == "alice"
    assert d["email"] == "a@x.com"
    assert d["team"] == "ops"
    assert d["notes"] == "critical"


def test_optional_fields_default_to_none(registry):
    registry.register("simple", "alice")
    entry = registry.get("simple")
    assert entry.email is None
    assert entry.team is None
    assert entry.notes is None
