"""Job dependency tracking: ensure dependent jobs only alert if their upstream jobs succeeded."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class DependencyGraph:
    """Tracks upstream/downstream relationships between cron jobs."""

    # job_name -> list of upstream job names that must have succeeded
    _deps: Dict[str, List[str]] = field(default_factory=dict)

    def register(self, job_name: str, depends_on: List[str]) -> None:
        """Register upstream dependencies for *job_name*."""
        if not job_name:
            raise ValueError("job_name must be a non-empty string")
        self._deps[job_name] = list(depends_on)

    def upstream(self, job_name: str) -> List[str]:
        """Return the list of upstream jobs for *job_name* (empty if none)."""
        return list(self._deps.get(job_name, []))

    def all_jobs(self) -> Set[str]:
        """Return all job names that have dependency entries."""
        return set(self._deps.keys())


class DependencyChecker:
    """Decides whether an alert for *job_name* should be suppressed because
    one or more upstream jobs have not succeeded recently."""

    def __init__(self, graph: DependencyGraph) -> None:
        self._graph = graph
        # job_name -> True means the job last ran successfully
        self._last_success: Dict[str, bool] = {}

    def record_success(self, job_name: str) -> None:
        """Mark *job_name* as having completed successfully."""
        self._last_success[job_name] = True

    def record_failure(self, job_name: str) -> None:
        """Mark *job_name* as having failed (clears success flag)."""
        self._last_success[job_name] = False

    def should_suppress(self, job_name: str) -> bool:
        """Return True if the alert for *job_name* should be suppressed because
        at least one upstream dependency has not succeeded."""
        for upstream in self._graph.upstream(job_name):
            if not self._last_success.get(upstream, False):
                return True
        return False

    def blocking_upstream(self, job_name: str) -> List[str]:
        """Return the upstream jobs that are currently blocking *job_name*."""
        return [
            up
            for up in self._graph.upstream(job_name)
            if not self._last_success.get(up, False)
        ]
