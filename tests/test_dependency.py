"""Tests for cronwatcher.dependency."""

import pytest

from cronwatcher.dependency import DependencyChecker, DependencyGraph


# ---------------------------------------------------------------------------
# DependencyGraph
# ---------------------------------------------------------------------------


def test_register_and_upstream():
    g = DependencyGraph()
    g.register("etl_load", ["etl_extract", "etl_transform"])
    assert g.upstream("etl_load") == ["etl_extract", "etl_transform"]


def test_upstream_unknown_job_returns_empty():
    g = DependencyGraph()
    assert g.upstream("nonexistent") == []


def test_register_empty_job_name_raises():
    g = DependencyGraph()
    with pytest.raises(ValueError, match="non-empty"):
        g.register("", ["upstream"])


def test_all_jobs_returns_registered_names():
    g = DependencyGraph()
    g.register("job_a", ["job_b"])
    g.register("job_c", [])
    assert g.all_jobs() == {"job_a", "job_c"}


def test_register_overwrites_previous_deps():
    g = DependencyGraph()
    g.register("job_a", ["job_b"])
    g.register("job_a", ["job_c", "job_d"])
    assert g.upstream("job_a") == ["job_c", "job_d"]


# ---------------------------------------------------------------------------
# DependencyChecker
# ---------------------------------------------------------------------------


@pytest.fixture()
def graph_with_deps() -> DependencyGraph:
    g = DependencyGraph()
    g.register("downstream", ["upstream_a", "upstream_b"])
    return g


@pytest.fixture()
def checker(graph_with_deps: DependencyGraph) -> DependencyChecker:
    return DependencyChecker(graph_with_deps)


def test_no_upstream_success_suppresses_alert(checker: DependencyChecker):
    assert checker.should_suppress("downstream") is True


def test_partial_upstream_success_still_suppresses(checker: DependencyChecker):
    checker.record_success("upstream_a")
    assert checker.should_suppress("downstream") is True


def test_all_upstream_success_allows_alert(checker: DependencyChecker):
    checker.record_success("upstream_a")
    checker.record_success("upstream_b")
    assert checker.should_suppress("downstream") is False


def test_failure_after_success_suppresses_again(checker: DependencyChecker):
    checker.record_success("upstream_a")
    checker.record_success("upstream_b")
    checker.record_failure("upstream_a")
    assert checker.should_suppress("downstream") is True


def test_blocking_upstream_lists_failed_deps(checker: DependencyChecker):
    checker.record_success("upstream_a")
    blocking = checker.blocking_upstream("downstream")
    assert blocking == ["upstream_b"]


def test_job_with_no_deps_never_suppressed():
    g = DependencyGraph()
    g.register("standalone", [])
    c = DependencyChecker(g)
    assert c.should_suppress("standalone") is False


def test_unknown_job_never_suppressed():
    g = DependencyGraph()
    c = DependencyChecker(g)
    assert c.should_suppress("ghost_job") is False
