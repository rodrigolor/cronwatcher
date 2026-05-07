"""Job metadata store: attach arbitrary key-value annotations to jobs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class JobMetadata:
    """Metadata annotations for a single cron job."""

    job_name: str
    annotations: Dict[str, str] = field(default_factory=dict)

    def set(self, key: str, value: str) -> None:
        if not key:
            raise ValueError("Metadata key must not be empty")
        self.annotations[key] = value

    def get(self, key: str) -> Optional[str]:
        return self.annotations.get(key)

    def remove(self, key: str) -> None:
        self.annotations.pop(key, None)

    def as_dict(self) -> dict:
        return {"job_name": self.job_name, "annotations": dict(self.annotations)}


class MetadataStore:
    """Persist job metadata as JSON files under a directory."""

    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.json"

    def save(self, metadata: JobMetadata) -> None:
        self._path(metadata.job_name).write_text(
            json.dumps(metadata.as_dict(), indent=2), encoding="utf-8"
        )

    def load(self, job_name: str) -> JobMetadata:
        path = self._path(job_name)
        if not path.exists():
            return JobMetadata(job_name=job_name)
        data = json.loads(path.read_text(encoding="utf-8"))
        return JobMetadata(
            job_name=data["job_name"],
            annotations=data.get("annotations", {}),
        )

    def all_jobs(self) -> list[str]:
        return [
            json.loads(p.read_text(encoding="utf-8"))["job_name"]
            for p in sorted(self._dir.glob("*.json"))
        ]

    def delete(self, job_name: str) -> None:
        path = self._path(job_name)
        if path.exists():
            path.unlink()
