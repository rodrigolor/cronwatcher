"""Runbook registry — attach remediation notes to jobs for use in alerts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RunbookEntry:
    job_name: str
    url: Optional[str] = None
    notes: Optional[str] = None
    steps: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a short human-readable summary of the runbook entry."""
        parts: List[str] = [f"Runbook for '{self.job_name}'"]
        if self.url:
            parts.append(f"  URL: {self.url}")
        if self.notes:
            parts.append(f"  Notes: {self.notes}")
        if self.steps:
            numbered = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(self.steps))
            parts.append(f"  Steps:\n{numbered}")
        return "\n".join(parts)


class RunbookRegistry:
    """In-memory store of runbook entries keyed by job name."""

    def __init__(self) -> None:
        self._entries: Dict[str, RunbookEntry] = {}

    def register(self, entry: RunbookEntry) -> None:
        if not entry.job_name:
            raise ValueError("job_name must not be empty")
        self._entries[entry.job_name] = entry

    def get(self, job_name: str) -> Optional[RunbookEntry]:
        return self._entries.get(job_name)

    def all_jobs(self) -> List[str]:
        return sorted(self._entries.keys())

    def remove(self, job_name: str) -> bool:
        if job_name in self._entries:
            del self._entries[job_name]
            return True
        return False


def build_registry_from_config(jobs_config: list) -> RunbookRegistry:
    """Populate a RunbookRegistry from a list of job config dicts."""
    registry = RunbookRegistry()
    for job in jobs_config:
        rb = job.get("runbook")
        if not rb:
            continue
        entry = RunbookEntry(
            job_name=job["name"],
            url=rb.get("url"),
            notes=rb.get("notes"),
            steps=rb.get("steps", []),
        )
        registry.register(entry)
    return registry
