"""Persistent execution history for cron jobs."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    job_name: str
    timestamp: str  # ISO-8601
    success: bool
    exit_code: Optional[int] = None
    message: Optional[str] = None

    @staticmethod
    def now(job_name: str, success: bool, exit_code: Optional[int] = None, message: Optional[str] = None) -> "ExecutionRecord":
        ts = datetime.now(tz=timezone.utc).isoformat()
        return ExecutionRecord(job_name=job_name, timestamp=ts, success=success, exit_code=exit_code, message=message)


class HistoryStore:
    """Append-only JSON-lines store for job execution history."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, entry: ExecutionRecord) -> None:
        """Append a single execution record to the store."""
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(entry)) + "\n")
        except OSError as exc:
            logger.error("Failed to write history record: %s", exc)

    def read_all(self) -> List[ExecutionRecord]:
        """Return all records from the store, oldest first."""
        records: List[ExecutionRecord] = []
        if not self._path.exists():
            return records
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        records.append(ExecutionRecord(**json.loads(line)))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.error("Failed to read history: %s", exc)
        return records

    def read_for_job(self, job_name: str) -> List[ExecutionRecord]:
        """Return all records for a specific job."""
        return [r for r in self.read_all() if r.job_name == job_name]

    def last_success(self, job_name: str) -> Optional[ExecutionRecord]:
        """Return the most recent successful execution for a job, or None."""
        records = [r for r in self.read_for_job(job_name) if r.success]
        return records[-1] if records else None

    def clear(self) -> None:
        """Remove all history (useful for testing)."""
        if self._path.exists():
            self._path.unlink()
