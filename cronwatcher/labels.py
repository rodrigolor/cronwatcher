"""Key-value label store for cron jobs.

Labels are arbitrary metadata attached to job names, useful for filtering,
grouping, and display in dashboards or reports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LabelStore:
    """In-memory store for job labels."""

    _data: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def set(self, job_name: str, key: str, value: str) -> None:
        """Attach a label key=value to a job."""
        if not job_name:
            raise ValueError("job_name must not be empty")
        if not key:
            raise ValueError("label key must not be empty")
        self._data.setdefault(job_name, {})[key] = value

    def get(self, job_name: str, key: str) -> Optional[str]:
        """Return the label value for a job/key pair, or None."""
        return self._data.get(job_name, {}).get(key)

    def get_all(self, job_name: str) -> Dict[str, str]:
        """Return all labels for a job (empty dict if none)."""
        return dict(self._data.get(job_name, {}))

    def remove(self, job_name: str, key: str) -> None:
        """Remove a single label from a job; no-op if absent."""
        self._data.get(job_name, {}).pop(key, None)

    def remove_all(self, job_name: str) -> None:
        """Remove all labels for a job."""
        self._data.pop(job_name, None)

    def jobs_with_label(self, key: str, value: Optional[str] = None) -> List[str]:
        """Return job names that have *key* (optionally matching *value*)."""
        result = []
        for job, labels in self._data.items():
            if key in labels:
                if value is None or labels[key] == value:
                    result.append(job)
        return sorted(result)

    def filter_jobs(
        self, job_names: List[str], key: str, value: Optional[str] = None
    ) -> List[str]:
        """Filter a list of job names to those matching the label criterion."""
        matching = set(self.jobs_with_label(key, value))
        return [j for j in job_names if j in matching]
