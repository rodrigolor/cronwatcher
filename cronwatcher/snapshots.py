"""Snapshot support: capture and compare scheduler state at a point in time."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from cronwatcher.scheduler import Scheduler


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SnapshotEntry:
    job_name: str
    last_seen: Optional[str]  # ISO-8601 or None
    missed: bool


@dataclass
class Snapshot:
    captured_at: str
    entries: List[SnapshotEntry] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "captured_at": self.captured_at,
            "entries": [asdict(e) for e in self.entries],
        }

    @staticmethod
    def from_dict(data: dict) -> "Snapshot":
        entries = [
            SnapshotEntry(**e) for e in data.get("entries", [])
        ]
        return Snapshot(captured_at=data["captured_at"], entries=entries)


class SnapshotManager:
    """Captures scheduler state snapshots and persists them to disk."""

    def __init__(self, directory: Path) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def capture(self, scheduler: Scheduler) -> Snapshot:
        now = _utcnow()
        missed_jobs = {r.job_name for r in scheduler.check_missed(now)}
        entries: List[SnapshotEntry] = []
        for job_name, state in scheduler._states.items():
            last_seen = state.last_seen.isoformat() if state.last_seen else None
            entries.append(SnapshotEntry(
                job_name=job_name,
                last_seen=last_seen,
                missed=job_name in missed_jobs,
            ))
        snapshot = Snapshot(
            captured_at=now.isoformat(),
            entries=sorted(entries, key=lambda e: e.job_name),
        )
        self._persist(snapshot)
        return snapshot

    def _persist(self, snapshot: Snapshot) -> None:
        filename = self._dir / f"snapshot_{snapshot.captured_at.replace(':', '-')}.json"
        filename.write_text(json.dumps(snapshot.as_dict(), indent=2))

    def list_snapshots(self) -> List[Path]:
        return sorted(self._dir.glob("snapshot_*.json"))

    def load_latest(self) -> Optional[Snapshot]:
        files = self.list_snapshots()
        if not files:
            return None
        data = json.loads(files[-1].read_text())
        return Snapshot.from_dict(data)

    def diff(self, a: Snapshot, b: Snapshot) -> Dict[str, dict]:
        """Return jobs whose state changed between two snapshots."""
        a_map = {e.job_name: e for e in a.entries}
        b_map = {e.job_name: e for e in b.entries}
        changed: Dict[str, dict] = {}
        for name in set(a_map) | set(b_map):
            ea = a_map.get(name)
            eb = b_map.get(name)
            if ea is None or eb is None or ea.missed != eb.missed or ea.last_seen != eb.last_seen:
                changed[name] = {
                    "before": asdict(ea) if ea else None,
                    "after": asdict(eb) if eb else None,
                }
        return changed
