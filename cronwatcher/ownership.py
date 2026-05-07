"""Job ownership registry — maps jobs to their responsible team or individual."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class OwnerEntry:
    job_name: str
    owner: str
    email: Optional[str] = None
    team: Optional[str] = None
    notes: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "owner": self.owner,
            "email": self.email,
            "team": self.team,
            "notes": self.notes,
        }


class OwnershipRegistry:
    """In-memory registry mapping job names to their owners."""

    def __init__(self) -> None:
        self._entries: Dict[str, OwnerEntry] = {}

    def register(
        self,
        job_name: str,
        owner: str,
        *,
        email: Optional[str] = None,
        team: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        if not job_name:
            raise ValueError("job_name must not be empty")
        if not owner:
            raise ValueError("owner must not be empty")
        self._entries[job_name] = OwnerEntry(
            job_name=job_name,
            owner=owner,
            email=email,
            team=team,
            notes=notes,
        )

    def get(self, job_name: str) -> Optional[OwnerEntry]:
        return self._entries.get(job_name)

    def remove(self, job_name: str) -> None:
        self._entries.pop(job_name, None)

    def all_entries(self) -> List[OwnerEntry]:
        return sorted(self._entries.values(), key=lambda e: e.job_name)

    def jobs_for_team(self, team: str) -> List[str]:
        return [
            e.job_name for e in self._entries.values() if e.team == team
        ]

    def jobs_for_owner(self, owner: str) -> List[str]:
        return [
            e.job_name for e in self._entries.values() if e.owner == owner
        ]
