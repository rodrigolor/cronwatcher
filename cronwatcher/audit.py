"""Audit log: records significant cronwatcher system events to a JSONL file."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEvent:
    event_type: str          # e.g. "job_missed", "job_failure", "alert_sent", "silence_added"
    job_name: Optional[str]
    detail: str
    timestamp: datetime = field(default_factory=_utcnow)

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "job_name": self.job_name,
            "detail": self.detail,
        }


class AuditLog:
    """Thread-safe append-only audit log backed by a JSONL file."""

    def __init__(self, log_dir: str | Path) -> None:
        self._path = Path(log_dir) / "audit.jsonl"
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def record(self, event: AuditEvent) -> None:
        """Append *event* to the audit log file."""
        line = json.dumps(event.as_dict()) + "\n"
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line)

    def read_all(self) -> list[AuditEvent]:
        """Return all recorded events in chronological order."""
        if not self._path.exists():
            return []
        events: list[AuditEvent] = []
        with self._path.open(encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                data = json.loads(raw)
                events.append(
                    AuditEvent(
                        event_type=data["event_type"],
                        job_name=data["job_name"],
                        detail=data["detail"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                    )
                )
        return events

    def read_for_job(self, job_name: str) -> list[AuditEvent]:
        """Return events that belong to *job_name*."""
        return [e for e in self.read_all() if e.job_name == job_name]

    def read_by_type(self, event_type: str) -> list[AuditEvent]:
        """Return events of a specific *event_type*."""
        return [e for e in self.read_all() if e.event_type == event_type]
