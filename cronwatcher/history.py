"""Persistent execution history store."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ExecutionRecord:
    job_name: str
    timestamp: datetime
    status: str  # "success" | "failure"
    exit_code: Optional[int] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None


_FIELDS = ["job_name", "timestamp", "status", "exit_code", "duration_seconds", "message"]


class HistoryStore:
    def __init__(self, directory: str) -> None:
        self._dir = directory
        os.makedirs(directory, exist_ok=True)

    def _path(self, job_name: str) -> str:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return os.path.join(self._dir, f"{safe}.csv")

    def record(self, rec: ExecutionRecord) -> None:
        path = self._path(rec.job_name)
        write_header = not os.path.exists(path)
        with open(path, "a", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow({
                "job_name": rec.job_name,
                "timestamp": rec.timestamp.isoformat(),
                "status": rec.status,
                "exit_code": "" if rec.exit_code is None else rec.exit_code,
                "duration_seconds": "" if rec.duration_seconds is None else rec.duration_seconds,
                "message": rec.message or "",
            })

    def read_all(self) -> List[ExecutionRecord]:
        records: List[ExecutionRecord] = []
        for fname in os.listdir(self._dir):
            if fname.endswith(".csv"):
                job = fname[:-4]
                records.extend(self._read_file(self._path(job)))
        return records

    def read_for_job(self, job_name: str) -> List[ExecutionRecord]:
        path = self._path(job_name)
        if not os.path.exists(path):
            return []
        return self._read_file(path)

    def list_jobs(self) -> List[str]:
        return [
            fname[:-4]
            for fname in os.listdir(self._dir)
            if fname.endswith(".csv")
        ]

    @staticmethod
    def _read_file(path: str) -> List[ExecutionRecord]:
        records: List[ExecutionRecord] = []
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                records.append(ExecutionRecord(
                    job_name=row["job_name"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    status=row["status"],
                    exit_code=int(row["exit_code"]) if row["exit_code"] else None,
                    duration_seconds=float(row["duration_seconds"]) if row["duration_seconds"] else None,
                    message=row["message"] or None,
                ))
        return records
