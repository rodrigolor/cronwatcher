"""Persistent execution history for cron jobs."""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class ExecutionRecord:
    job_name: str
    timestamp: datetime
    success: bool
    exit_code: Optional[int]
    message: str


_FIELDS = ["job_name", "timestamp", "success", "exit_code", "message"]


class HistoryStore:
    def __init__(self, data_dir: str):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: Optional[str] = None) -> Path:
        if job_name:
            safe = job_name.replace("/", "_").replace(" ", "_")
            return self._dir / f"{safe}.csv"
        return self._dir / "history.csv"

    def record(self, rec: ExecutionRecord) -> None:
        path = self._path(rec.job_name)
        write_header = not path.exists()
        with path.open("a", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(
                {
                    "job_name": rec.job_name,
                    "timestamp": rec.timestamp.isoformat(),
                    "success": str(rec.success),
                    "exit_code": "" if rec.exit_code is None else str(rec.exit_code),
                    "message": rec.message,
                }
            )

    def _parse_row(self, row: dict) -> ExecutionRecord:
        return ExecutionRecord(
            job_name=row["job_name"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            success=row["success"].lower() == "true",
            exit_code=int(row["exit_code"]) if row["exit_code"] else None,
            message=row["message"],
        )

    def read_all(self) -> List[ExecutionRecord]:
        records: List[ExecutionRecord] = []
        for csv_file in self._dir.glob("*.csv"):
            with csv_file.open(newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    records.append(self._parse_row(row))
        return records

    def read_for_job(self, job_name: str) -> List[ExecutionRecord]:
        path = self._path(job_name)
        if not path.exists():
            return []
        with path.open(newline="") as fh:
            reader = csv.DictReader(fh)
            return [self._parse_row(row) for row in reader]

    def rewrite(self, records: List[ExecutionRecord]) -> None:
        """Overwrite all per-job CSV files with the given records."""
        # Clear existing files
        for csv_file in self._dir.glob("*.csv"):
            csv_file.unlink()
        for rec in records:
            self.record(rec)
