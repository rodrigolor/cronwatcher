"""Silence windows: suppress alerts for jobs during scheduled maintenance."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class SilenceWindow:
    """A time window during which alerts for a job are suppressed."""

    job_name: str
    start: datetime  # UTC
    end: datetime    # UTC
    reason: str = ""

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if the silence window covers *at* (defaults to now)."""
        now = at or datetime.now(timezone.utc)
        return self.start <= now <= self.end


@dataclass
class SilenceRegistry:
    """In-memory registry of silence windows."""

    _windows: List[SilenceWindow] = field(default_factory=list)

    def add(self, window: SilenceWindow) -> None:
        """Register a new silence window."""
        self._windows.append(window)

    def remove_expired(self, at: Optional[datetime] = None) -> int:
        """Purge windows that have already ended. Returns the number removed."""
        now = at or datetime.now(timezone.utc)
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.end >= now]
        return before - len(self._windows)

    def is_silenced(self, job_name: str, at: Optional[datetime] = None) -> bool:
        """Return True if *job_name* has an active silence window at *at*."""
        return any(
            w.job_name == job_name and w.is_active(at)
            for w in self._windows
        )

    def active_windows(self, at: Optional[datetime] = None) -> List[SilenceWindow]:
        """Return all currently active windows."""
        return [w for w in self._windows if w.is_active(at)]

    def windows_for_job(self, job_name: str) -> List[SilenceWindow]:
        """Return all windows (active or not) registered for *job_name*."""
        return [w for w in self._windows if w.job_name == job_name]
