"""Tag-based filtering for cron jobs.

Allows jobs to be grouped by tags so that alerts, reports, and dashboards
can be filtered to a specific subset of jobs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set, Dict, List


@dataclass
class TagRegistry:
    """Maps job names to their associated tags and vice-versa."""

    _job_tags: Dict[str, Set[str]] = field(default_factory=dict)
    _tag_jobs: Dict[str, Set[str]] = field(default_factory=dict)

    def register(self, job_name: str, tags: Iterable[str]) -> None:
        """Associate *tags* with *job_name*, replacing any previous tags."""
        old_tags = self._job_tags.pop(job_name, set())
        for tag in old_tags:
            self._tag_jobs.get(tag, set()).discard(job_name)

        tag_set: Set[str] = set(tags)
        self._job_tags[job_name] = tag_set
        for tag in tag_set:
            self._tag_jobs.setdefault(tag, set()).add(job_name)

    def tags_for_job(self, job_name: str) -> Set[str]:
        """Return the set of tags for *job_name* (empty set if unknown)."""
        return set(self._job_tags.get(job_name, set()))

    def jobs_for_tag(self, tag: str) -> Set[str]:
        """Return all job names that carry *tag*."""
        return set(self._tag_jobs.get(tag, set()))

    def filter_jobs(self, job_names: Iterable[str], tags: Iterable[str]) -> List[str]:
        """Return only those *job_names* that have at least one of *tags*.

        If *tags* is empty the original list is returned unchanged.
        """
        tag_set = set(tags)
        if not tag_set:
            return list(job_names)
        return [
            name for name in job_names
            if self._job_tags.get(name, set()) & tag_set
        ]

    def all_tags(self) -> Set[str]:
        """Return the set of all registered tags."""
        return set(self._tag_jobs.keys())

    def remove_job(self, job_name: str) -> None:
        """Remove *job_name* and clean up reverse index."""
        for tag in self._job_tags.pop(job_name, set()):
            self._tag_jobs.get(tag, set()).discard(job_name)
