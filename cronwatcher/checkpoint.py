"""Checkpoint module: persist and restore last-known-good execution timestamps."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CheckpointEntry:
    job_name: str
    last_success: datetime
    run_count: int = 0

    def as_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_success": self.last_success.isoformat(),
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointEntry":
        return cls(
            job_name=data["job_name"],
            last_success=datetime.fromisoformat(data["last_success"]),
            run_count=data.get("run_count", 0),
        )


class CheckpointStore:
    """Persist per-job last-success checkpoints to a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def _load(self) -> Dict[str, dict]:
        if not self._path.exists():
            return {}
        with self._path.open() as fh:
            return json.load(fh)

    def _save(self, data: Dict[str, dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as fh:
            json.dump(data, fh, indent=2)

    def record_success(self, job_name: str, ts: Optional[datetime] = None) -> CheckpointEntry:
        """Record a successful execution for *job_name* at *ts* (defaults to now)."""
        if not job_name:
            raise ValueError("job_name must not be empty")
        ts = ts or _utcnow()
        data = self._load()
        prev = data.get(job_name, {})
        entry = CheckpointEntry(
            job_name=job_name,
            last_success=ts,
            run_count=prev.get("run_count", 0) + 1,
        )
        data[job_name] = entry.as_dict()
        self._save(data)
        return entry

    def get(self, job_name: str) -> Optional[CheckpointEntry]:
        """Return the latest checkpoint for *job_name*, or None if not found."""
        data = self._load()
        raw = data.get(job_name)
        if raw is None:
            return None
        return CheckpointEntry.from_dict(raw)

    def all_entries(self) -> list[CheckpointEntry]:
        """Return all stored checkpoints sorted by job name."""
        data = self._load()
        return [CheckpointEntry.from_dict(v) for v in sorted(data.values(), key=lambda d: d["job_name"])]

    def clear(self, job_name: str) -> bool:
        """Remove the checkpoint for *job_name*. Returns True if it existed."""
        data = self._load()
        if job_name not in data:
            return False
        del data[job_name]
        self._save(data)
        return True
