"""History retention policy: prune old execution records."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from cronwatcher.history import HistoryStore, ExecutionRecord

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class RetentionPolicy:
    """Defines how long execution records should be kept."""

    def __init__(self, max_age_days: int = 30, max_records_per_job: Optional[int] = 500):
        if max_age_days <= 0:
            raise ValueError("max_age_days must be positive")
        self.max_age_days = max_age_days
        self.max_records_per_job = max_records_per_job

    def is_expired(self, record: ExecutionRecord, now: Optional[datetime] = None) -> bool:
        cutoff = (now or _utcnow()) - timedelta(days=self.max_age_days)
        return record.timestamp < cutoff


class RetentionManager:
    """Applies a RetentionPolicy to a HistoryStore, pruning stale records."""

    def __init__(self, store: HistoryStore, policy: RetentionPolicy):
        self._store = store
        self._policy = policy

    def prune(self, now: Optional[datetime] = None) -> int:
        """Remove expired / excess records. Returns total records deleted."""
        all_records = self._store.read_all()
        if not all_records:
            return 0

        # Group by job name
        by_job: dict[str, list[ExecutionRecord]] = {}
        for rec in all_records:
            by_job.setdefault(rec.job_name, []).append(rec)

        kept: list[ExecutionRecord] = []
        removed = 0

        for job_name, records in by_job.items():
            # Sort newest first
            records.sort(key=lambda r: r.timestamp, reverse=True)

            # Apply age filter
            fresh = [r for r in records if not self._policy.is_expired(r, now)]

            # Apply per-job cap
            if self._policy.max_records_per_job is not None:
                fresh = fresh[: self._policy.max_records_per_job]

            job_removed = len(records) - len(fresh)
            if job_removed:
                logger.info("Pruned %d record(s) for job '%s'", job_removed, job_name)
            removed += job_removed
            kept.extend(fresh)

        if removed:
            self._store.rewrite(kept)

        return removed
