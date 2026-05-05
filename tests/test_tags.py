"""Tests for cronwatcher.tags.TagRegistry."""
from __future__ import annotations

import pytest

from cronwatcher.tags import TagRegistry


@pytest.fixture()
def registry() -> TagRegistry:
    reg = TagRegistry()
    reg.register("backup", ["infra", "nightly"])
    reg.register("cleanup", ["nightly"])
    reg.register("report", ["business"])
    return reg


def test_tags_for_known_job(registry: TagRegistry) -> None:
    assert registry.tags_for_job("backup") == {"infra", "nightly"}


def test_tags_for_unknown_job_returns_empty(registry: TagRegistry) -> None:
    assert registry.tags_for_job("nonexistent") == set()


def test_jobs_for_tag(registry: TagRegistry) -> None:
    assert registry.jobs_for_tag("nightly") == {"backup", "cleanup"}


def test_jobs_for_unknown_tag_returns_empty(registry: TagRegistry) -> None:
    assert registry.jobs_for_tag("unknown") == set()


def test_filter_jobs_with_matching_tag(registry: TagRegistry) -> None:
    jobs = ["backup", "cleanup", "report"]
    result = registry.filter_jobs(jobs, ["nightly"])
    assert sorted(result) == ["backup", "cleanup"]


def test_filter_jobs_no_tags_returns_all(registry: TagRegistry) -> None:
    jobs = ["backup", "cleanup", "report"]
    assert registry.filter_jobs(jobs, []) == jobs


def test_filter_jobs_no_match_returns_empty(registry: TagRegistry) -> None:
    assert registry.filter_jobs(["backup"], ["business"]) == []


def test_all_tags(registry: TagRegistry) -> None:
    assert registry.all_tags() == {"infra", "nightly", "business"}


def test_register_replaces_old_tags(registry: TagRegistry) -> None:
    registry.register("backup", ["weekly"])
    assert registry.tags_for_job("backup") == {"weekly"}
    # old tags should no longer reference backup
    assert "backup" not in registry.jobs_for_tag("infra")
    assert "backup" not in registry.jobs_for_tag("nightly")
    assert "backup" in registry.jobs_for_tag("weekly")


def test_remove_job(registry: TagRegistry) -> None:
    registry.remove_job("backup")
    assert registry.tags_for_job("backup") == set()
    assert "backup" not in registry.jobs_for_tag("infra")
    assert "backup" not in registry.jobs_for_tag("nightly")


def test_remove_unknown_job_does_not_raise(registry: TagRegistry) -> None:
    registry.remove_job("ghost")  # should not raise
