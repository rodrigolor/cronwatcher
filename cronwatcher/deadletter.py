"""Dead-letter queue: persist alerts that could not be delivered for later replay."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DeadLetter:
    job_name: str
    alert_type: str  # 'missed' | 'failure'
    message: str
    created_at: datetime = field(default_factory=_utcnow)
    attempts: int = 0

    def as_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "alert_type": self.alert_type,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DeadLetter":
        return cls(
            job_name=d["job_name"],
            alert_type=d["alert_type"],
            message=d["message"],
            created_at=datetime.fromisoformat(d["created_at"]),
            attempts=d.get("attempts", 0),
        )


class DeadLetterQueue:
    """Append-only file-backed queue of undelivered alerts."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def push(self, letter: DeadLetter) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(letter.as_dict()) + "\n")

    def read_all(self) -> List[DeadLetter]:
        if not self._path.exists():
            return []
        letters: List[DeadLetter] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    letters.append(DeadLetter.from_dict(json.loads(line)))
        return letters

    def clear(self) -> None:
        """Remove all entries (call after successful replay)."""
        if self._path.exists():
            self._path.unlink()

    def rewrite(self, letters: List[DeadLetter]) -> None:
        """Replace queue contents with the given list."""
        if self._path.exists():
            self._path.unlink()
        for letter in letters:
            self.push(letter)
