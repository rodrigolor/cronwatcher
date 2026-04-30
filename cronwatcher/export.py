"""Export execution history to JSON or CSV formats."""
from __future__ import annotations

import csv
import io
import json
from typing import List, Literal

from cronwatcher.history import ExecutionRecord, HistoryStore

ExportFormat = Literal["json", "csv"]


def _records_to_dicts(records: List[ExecutionRecord]) -> List[dict]:
    return [
        {
            "job_name": r.job_name,
            "timestamp": r.timestamp.isoformat(),
            "success": r.success,
            "exit_code": r.exit_code,
            "duration_seconds": r.duration_seconds,
            "message": r.message,
        }
        for r in records
    ]


def export_json(records: List[ExecutionRecord], indent: int = 2) -> str:
    """Serialize records to a JSON string."""
    return json.dumps(_records_to_dicts(records), indent=indent)


def export_csv(records: List[ExecutionRecord]) -> str:
    """Serialize records to a CSV string."""
    fieldnames = ["job_name", "timestamp", "success", "exit_code", "duration_seconds", "message"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_records_to_dicts(records))
    return buf.getvalue()


def export_history(
    store: HistoryStore,
    fmt: ExportFormat = "json",
    job_name: str | None = None,
) -> str:
    """Export history from *store* in the requested format.

    Args:
        store: The :class:`HistoryStore` to read from.
        fmt: ``"json"`` (default) or ``"csv"``.
        job_name: When provided, only records for that job are included.

    Returns:
        A string containing the serialised data.
    """
    if job_name:
        records = store.read_for_job(job_name)
    else:
        records = store.read_all()

    if fmt == "csv":
        return export_csv(records)
    return export_json(records)
